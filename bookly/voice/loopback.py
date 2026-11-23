"""Phone-path test without a phone: pretend to be Twilio.

Connects to the running server's /media WebSocket, speaks scripted caller
lines (synthesized by Cartesia, streamed in real time with background
silence like a real call), plays back agent audio on a simulated clock,
echoes playback marks, honours "clear" (barge-in), and measures time to first
audio: from the end of the caller's speech to the first agent audio back.

    .venv/bin/python -m bookly.voice.loopback --phone +13125550142
    .venv/bin/python -m bookly.voice.loopback --script barge          # talk over the agent
    .venv/bin/python -m bookly.voice.loopback --silent                # reprompt + hang-up
    .venv/bin/python -m bookly.voice.loopback --ab-streaming 2        # streaming on vs off, interleaved
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

# Each line: (text, interrupt_after_s). None = wait for the agent to finish first;
# a number = start talking that many seconds after the agent starts answering the previous line.
SCRIPTS = {
    "happy": ("+13125550142", [
        ("Hi, I'm calling about my order of Project Hail Mary. When will it get here?", None),
        ("Yes please, text me the tracking number.", None),
        ("No, that's everything. Thanks, bye.", None),
    ]),
    "clarify": ("+14155550101", [
        ("Hi, I'm calling to check on my order.", None),
        ("The one with two books in it, Klara and the Sun.", None),
        ("Great, that's all. Thank you, bye.", None),
    ]),
    # The demo call script (docs: "Bookly Demo Call Script"): Maya, then the no-setup backup, Sofia.
    "demo_maya": ("+14155550101", [
        ("Hi, I'm calling to check on my order.", None),
        ("The one with two books. Klara and the Sun was one of them.", None),
        ("Great. Actually, I want to return Klara and the Sun. A friend gave me a copy for my birthday.", None),
        ("Nine, four, one, one, zero.", None),
        ("No thanks, I'd rather have a refund.", None),
        ("Yes, go ahead.", None),
        ("No receipt, thanks. One more thing: can I also return Educated by Tara Westover? "
         "I never got around to reading it.", None),
        ("No thanks, that's fine. That's everything. Bye.", None),
    ]),
    "demo_sofia": ("+15125550199", [
        ("Hi, I'm checking on an order I placed for Lessons in Chemistry.", None),
        ("It's four, two, zero, zero, four, four.", None),
        ("Oh good, then please cancel it. I found it at a local shop.", None),
        ("One, one, two, one, five.", None),
        ("Yes.", None),
        ("Email is fine. That's all, thanks.", None),
    ]),
    "angry": ("+16175550188", [
        ("This is the third time I'm calling. My book never showed up and nobody has fixed it!", None),
    ]),
    "barge": ("+13125550142", [
        ("Hi, when will my Project Hail Mary order get here?", None),
        ("Sorry, actually, can you just text me the tracking number?", 1.2),
        ("No, that's all. Thanks, bye.", None),
    ]),
}


class FakeTwilio:
    def __init__(self, ws):
        self.ws = ws
        self.speaking = False
        self.speech: list[bytes] = []
        self.play_until = 0.0
        self.last_media_at = 0.0
        self.first_media_after: float | None = None
        self.waiting_since: float | None = None
        self.pending_marks: dict[str, asyncio.TimerHandle] = {}
        self.clears = 0
        self.closed = asyncio.Event()

    async def send(self, obj):
        try:
            await self.ws.send(json.dumps(obj))
        except Exception:
            self.closed.set()

    def _echo_mark(self, name: str):
        self.pending_marks.pop(name, None)
        asyncio.ensure_future(self.send({"event": "mark", "streamSid": "MZloop", "mark": {"name": name}}))

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
                    self.play_until = max(self.play_until, now) + len(audio) / 8000
                    self.last_media_at = now
                    if self.waiting_since and self.first_media_after is None:
                        self.first_media_after = now
                elif msg["event"] == "mark":
                    name = msg["mark"]["name"]
                    self.pending_marks[name] = asyncio.get_running_loop().call_later(
                        max(0.0, self.play_until - now), self._echo_mark, name)
                elif msg["event"] == "clear":  # Twilio drops buffered audio and returns pending marks
                    self.clears += 1
                    self.play_until = now
                    for name, h in list(self.pending_marks.items()):
                        h.cancel()
                        self._echo_mark(name)
        except Exception:
            pass
        self.closed.set()

    async def wait_reply_start(self, timeout: float = 40):
        end = time.monotonic() + timeout
        while self.first_media_after is None and time.monotonic() < end and not self.closed.is_set():
            await asyncio.sleep(0.02)

    async def agent_idle(self, quiet_s: float = 1.5, timeout: float = 40):
        await self.wait_reply_start(timeout)
        end = time.monotonic() + timeout
        while time.monotonic() < end and not self.closed.is_set():
            now = time.monotonic()
            if now > self.play_until + quiet_s and now - self.last_media_at > quiet_s:
                return
            await asyncio.sleep(0.1)

    async def say(self, audio: bytes):
        self.speech = [audio[i:i + FRAME] for i in range(0, len(audio), FRAME)]
        self.speaking = True
        while self.speaking and not self.closed.is_set():
            await asyncio.sleep(0.02)


async def run_call(url: str, phone: str, lines: list[tuple[str, float | None]], audio: list[bytes],
                   streaming: str | None = None, quiet: bool = False) -> dict:
    out = {"ttfa": [], "clears": 0, "hung_up_after_s": None}
    log = (lambda *a: None) if quiet else print
    async with connect(url, max_size=None) as ws:
        tw = FakeTwilio(ws)
        params = {"caller": phone}
        if streaming is not None:
            params["streaming"] = streaming
        await tw.send({"event": "connected", "protocol": "Call", "version": "1.0.0"})
        await tw.send({"event": "start", "streamSid": "MZloop",
                       "start": {"streamSid": "MZloop", "callSid": f"CAloop{time.time_ns()}",
                                 "customParameters": params}})
        up, down = asyncio.create_task(tw.uplink()), asyncio.create_task(tw.downlink())
        tw.waiting_since = time.monotonic()
        await tw.agent_idle()
        log("greeting played")
        i = 0
        while i < len(lines) and not tw.closed.is_set():
            text, _ = lines[i]
            await tw.say(audio[i])
            log(f"caller: {text}")
            nxt = lines[i + 1] if i + 1 < len(lines) else None
            if nxt and nxt[1] is not None:       # next line interrupts this reply
                await tw.wait_reply_start()
                ttfa = round((tw.first_media_after - tw.waiting_since) * 1000) if tw.first_media_after else None
                out["ttfa"].append(ttfa)
                log(f"   time to first audio: {ttfa} ms; interrupting in {nxt[1]} s")
                await asyncio.sleep(nxt[1])
            else:
                await tw.agent_idle()
                ttfa = round((tw.first_media_after - tw.waiting_since) * 1000) if tw.first_media_after else None
                out["ttfa"].append(ttfa)
                log(f"   time to first audio: {ttfa} ms")
            i += 1
        if not lines:  # silent caller: wait for the server to hang up on us
            t0 = time.monotonic()
            try:
                await asyncio.wait_for(tw.closed.wait(), timeout=45)
                out["hung_up_after_s"] = round(time.monotonic() - t0, 1)
                log(f"server hung up {out['hung_up_after_s']} s after the greeting finished")
            except asyncio.TimeoutError:
                log("server did NOT hang up within 45 s")
        await asyncio.sleep(1)
        if not tw.closed.is_set():
            await tw.send({"event": "stop", "streamSid": "MZloop"})
        out["clears"] = tw.clears
        up.cancel()
        down.cancel()
    return out


async def synth_lines(lines):
    if not lines:
        return []
    tts = TTS()
    await tts.start()
    try:
        return [await tts.synth(t) for t, _ in lines]
    finally:
        await tts.close()


def _stats(xs):
    xs = [x for x in xs if x is not None]
    return f"p50 {int(statistics.median(xs))} ms, max {max(xs)} ms, n={len(xs)}" if xs else "no data"


async def main_async(args):
    if args.ab_streaming:
        jobs = []
        for r in range(args.ab_streaming):
            for name in ("happy", "clarify"):
                for streaming in ("1", "0") if r % 2 == 0 else ("0", "1"):
                    jobs.append((name, streaming))
        audio = {n: await synth_lines(SCRIPTS[n][1]) for n in ("happy", "clarify")}
        sem = asyncio.Semaphore(4)

        async def one(name, streaming):
            async with sem:
                phone, lines = SCRIPTS[name]
                return streaming, await run_call(args.url, phone, lines, audio[name], streaming, quiet=True)
        results = await asyncio.gather(*(one(n, s) for n, s in jobs))
        for s in ("0", "1"):
            vals = [v for st, r in results if st == s for v in r["ttfa"]]
            print(f"streaming={'on ' if s == '1' else 'off'}  time to first audio: {_stats(vals)}")
        print("Per-turn server breakdown: voice_turn events in logs/call-*.jsonl")
        return
    if args.silent:
        lines, phone = [], args.phone or "+13125550142"
    else:
        phone, lines = SCRIPTS[args.script]
        phone = args.phone or phone
    out = await run_call(args.url, phone, lines, await synth_lines(lines))
    print(f"time to first audio (end of caller speech -> first agent audio): {_stats(out['ttfa'])}; "
          f"clear events: {out['clears']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://localhost:8080/media")
    ap.add_argument("--script", choices=sorted(SCRIPTS), default="happy")
    ap.add_argument("--phone", help="Override the script's caller ID")
    ap.add_argument("--silent", action="store_true", help="Say nothing: expect one reprompt, then goodbye + hang-up")
    ap.add_argument("--ab-streaming", type=int, metavar="ROUNDS",
                    help="Run happy + clarify with streaming on and off, interleaved, ROUNDS times")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
