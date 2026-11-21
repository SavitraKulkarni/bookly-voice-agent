"""Phone-path test without a phone: pretend to be Twilio.

Connects to the running server's /media WebSocket, speaks scripted caller
lines (synthesized by Cartesia, streamed in real time with background
silence like a real call), echoes playback marks, and measures time to first
audio: from the end of the caller's speech to the first agent audio back.
This includes STT endpointing, the agent, and TTS: everything but the phone network.

    .venv/bin/python -m bookly.voice.server &
    .venv/bin/python -m bookly.voice.loopback --phone +13125550142
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import statistics
import time

from websockets.asyncio.client import connect

import bookly.agent  # noqa: F401  (loads .env)
from bookly.voice.tts import TTS

FRAME = 160          # 20 ms of 8 kHz mu-law, what Twilio sends
SILENCE = b"\xff" * FRAME
SCRIPTS = {
    "+13125550142": [  # James: happy path, order status + tracking text
        "Hi, I'm calling about my order of Project Hail Mary. When will it get here?",
        "Yes please, text me the tracking number.",
        "No, that's everything. Thanks, bye.",
    ],
    "+14155550101": [  # Maya: clarifying question
        "Hi, I'm calling to check on my order.",
        "The one with two books in it, Klara and the Sun.",
        "Great, that's all. Thank you, bye.",
    ],
}


class FakeTwilio:
    def __init__(self, ws):
        self.ws = ws
        self.speaking = False
        self.speech: list[bytes] = []
        self.play_until = 0.0          # when our simulated phone finishes playing agent audio
        self.last_media_at = 0.0
        self.first_media_after: float | None = None
        self.waiting_since: float | None = None
        self.agent_audio_bytes = 0
        self.closed = asyncio.Event()

    async def send(self, obj):
        await self.ws.send(json.dumps(obj))

    async def uplink(self):
        """Stream caller audio continuously (speech when talking, silence otherwise), real-time paced."""
        t = time.monotonic()
        while not self.closed.is_set():
            frame = self.speech.pop(0) if self.speech else SILENCE
            if not self.speech and self.speaking:
                self.speaking = False
                self.waiting_since = time.monotonic()  # caller just stopped talking
                self.first_media_after = None
            await self.send({"event": "media", "streamSid": "MZloop",
                             "media": {"track": "inbound", "payload": base64.b64encode(frame).decode()}})
            t += 0.02
            await asyncio.sleep(max(0, t - time.monotonic()))

    async def downlink(self):
        try:
            async for raw in self.ws:
                msg = json.loads(raw)
                now = time.monotonic()
                if msg["event"] == "media":
                    audio = base64.b64decode(msg["media"]["payload"])
                    self.agent_audio_bytes += len(audio)
                    self.play_until = max(self.play_until, now) + len(audio) / 8000
                    self.last_media_at = now
                    if self.waiting_since and self.first_media_after is None:
                        self.first_media_after = now
                elif msg["event"] == "mark":
                    delay = max(0.0, self.play_until - now)
                    asyncio.get_running_loop().call_later(
                        delay, lambda n=msg["mark"]["name"]: asyncio.ensure_future(
                            self.send({"event": "mark", "streamSid": "MZloop", "mark": {"name": n}})))
        except Exception:
            pass
        self.closed.set()

    async def agent_idle(self, quiet_s: float = 1.5, timeout: float = 40, expect_reply: bool = True):
        end = time.monotonic() + timeout
        while expect_reply and self.first_media_after is None and time.monotonic() < end \
                and not self.closed.is_set():
            await asyncio.sleep(0.02)   # agent hasn't started answering yet
        while time.monotonic() < end and not self.closed.is_set():
            now = time.monotonic()
            if now > self.play_until + quiet_s and now - self.last_media_at > quiet_s:
                return
            await asyncio.sleep(0.1)


async def main_async(url: str, phone: str, lines: list[str]):
    caller_audio = []
    if lines:
        tts = TTS()
        await tts.start()
        caller_audio = [await tts.synth(line) for line in lines]
        await tts.close()

    results = []
    async with connect(url, max_size=None) as ws:
        tw = FakeTwilio(ws)
        await tw.send({"event": "connected", "protocol": "Call", "version": "1.0.0"})
        await tw.send({"event": "start", "streamSid": "MZloop",
                       "start": {"streamSid": "MZloop", "callSid": f"CAloop{int(time.time())}",
                                 "customParameters": {"caller": phone}}})
        up, down = asyncio.create_task(tw.uplink()), asyncio.create_task(tw.downlink())
        tw.waiting_since = time.monotonic()
        await tw.agent_idle()                       # greeting
        print("greeting played")
        for line, audio in zip(lines, caller_audio):
            if tw.closed.is_set():
                break
            tw.speech = [audio[i:i + FRAME] for i in range(0, len(audio), FRAME)]
            tw.speaking = True
            print(f"caller: {line}")
            while tw.speaking:
                await asyncio.sleep(0.02)
            await tw.agent_idle()
            ttfa = round((tw.first_media_after - tw.waiting_since) * 1000) if tw.first_media_after else None
            results.append(ttfa)
            print(f"   time to first audio: {ttfa} ms")
        if not lines:  # silent caller: wait for the server to hang up on us
            t0 = time.monotonic()
            try:
                await asyncio.wait_for(tw.closed.wait(), timeout=45)
                print(f"server hung up {time.monotonic() - t0:.1f} s after the greeting finished")
            except asyncio.TimeoutError:
                print("server did NOT hang up within 45 s")
        await asyncio.sleep(1)
        if not tw.closed.is_set():
            await tw.send({"event": "stop", "streamSid": "MZloop"})
        up.cancel()
        down.cancel()
    vals = [r for r in results if r is not None]
    if vals:
        print(f"time to first audio (end of caller speech -> first agent audio): "
              f"p50 {int(statistics.median(vals))} ms, max {max(vals)} ms over {len(vals)} turns")
    print("Server-side breakdown is in the call log (voice_turn events) in logs/.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://localhost:8080/media")
    ap.add_argument("--phone", default="+13125550142")
    ap.add_argument("--silent", action="store_true", help="Say nothing: expect one reprompt, then goodbye + hang-up")
    args = ap.parse_args()
    lines = [] if args.silent else SCRIPTS.get(args.phone, SCRIPTS["+13125550142"])
    asyncio.run(main_async(args.url, args.phone, lines))


if __name__ == "__main__":
    main()
