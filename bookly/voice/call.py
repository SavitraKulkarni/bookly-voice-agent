"""One phone call: Twilio media stream <-> STT <-> Agent <-> TTS.

The agent is the same object the text CLI uses; this file only adds what a
phone line needs: audio in/out, a filler line while tools run, a silence
reprompt, hang-up, and time-to-first-audio measurement.
"""
from __future__ import annotations

import asyncio
import base64
import json
import statistics
import time
from typing import Any

from bookly import db
from bookly.agent import GREETING, Agent
from bookly.voice.stt import STTStream
from bookly.voice.tts import TTS

SILENCE_REPROMPT_S = 8.0
LOOKUP_TOOLS = {"lookup_customer", "lookup_order", "search_faq", "verify_zip", "send_confirmation"}
WRITE_TOOLS = {"cancel_order", "start_return", "issue_store_credit", "send_password_reset"}

PHRASES = {
    "greeting": GREETING,
    "filler_lookup": "Let me pull that up.",
    "filler_write": "One moment while I take care of that.",
    "reprompt": "Are you still there?",
    "silence_bye": "I haven't heard anything, so I'll end the call now. Thanks for calling Bookly. Goodbye.",
}
_phrase_audio: dict[str, bytes] = {}


async def load_phrases() -> None:
    """Pre-synthesize fixed lines once so they play instantly (zero TTS latency)."""
    if _phrase_audio:
        return
    tts = TTS()
    await tts.start()
    try:
        for key, text in PHRASES.items():
            _phrase_audio[key] = await tts.synth(text)
    finally:
        await tts.close()


def _p50(xs: list[int]) -> int | None:
    return int(statistics.median(xs)) if xs else None


class CallSession:
    def __init__(self, twilio_ws, stream_sid: str, call_sid: str, caller: str | None):
        self.twilio = twilio_ws
        self.stream_sid, self.call_sid = stream_sid, call_sid
        self.loop = asyncio.get_running_loop()
        self.agent = Agent(caller_id=caller, call_id=f"call-{call_sid[-10:]}", on_tool_start=self._on_tool_start)
        self.log = self.agent.log
        conn = db.connect()
        self.stt = STTStream(db.catalog_titles(conn) + ["Bookly"], on_final=self._on_final, on_speech=self._on_speech)
        conn.close()
        self.tts = TTS()

        self.pending: list[tuple[str, dict]] = []
        self.busy = False
        self.ended = False
        self.marks: set[str] = set()
        self.playback_idle = asyncio.Event()
        self.playback_idle.set()
        self.silence_task: asyncio.Task | None = None
        self.reprompts = 0
        self.turn: dict[str, Any] | None = None   # timing for the turn in flight
        self.turn_metrics: list[dict[str, Any]] = []
        self._mark_n = 0

    # ---- lifecycle --------------------------------------------------------
    async def start(self) -> None:
        self.log.event("phone_call_start", call_sid=self.call_sid, stream_sid=self.stream_sid)
        await asyncio.gather(self.stt.start(), self.tts.start())
        self.agent.greeting()
        await self._play(_phrase_audio["greeting"], "greeting")

    async def close(self, reason: str = "stream_stopped") -> None:
        if getattr(self, "_closed", False):
            return
        self._closed = True
        self.ended = True
        if not self.agent.state.end_reason:
            self.agent.state.end_reason = "caller_hung_up"  # stream closed before the agent ended the call
        if self.silence_task:
            self.silence_task.cancel()
        await asyncio.gather(self.stt.close(), self.tts.close(), return_exceptions=True)
        firsts = [m["ttfa_ms"] for m in self.turn_metrics if m.get("ttfa_ms") is not None]
        answers = [m["ttfa_answer_ms"] for m in self.turn_metrics if m.get("ttfa_answer_ms") is not None]
        stt = [m["stt_endpoint_ms"] for m in self.turn_metrics if m.get("stt_endpoint_ms") is not None]
        self.agent.extra_summary["voice"] = {
            "turns": len(self.turn_metrics),
            "ttfa_ms_p50": _p50(firsts), "ttfa_ms_max": max(firsts, default=None),
            "ttfa_answer_ms_p50": _p50(answers), "ttfa_answer_ms_max": max(answers, default=None),
            "stt_endpoint_ms_p50": _p50(stt),
            "fillers_played": sum(1 for m in self.turn_metrics if m.get("filler")),
            "reprompts": self.reprompts, "close_reason": reason,
            "stt_model": self.stt.config.get("model"), "stt_mode": self.stt.config.get("mode"),
        }
        summary = self.agent.end()
        print(f"[call end] {json.dumps(summary, default=str)}")

    # ---- Twilio in/out ----------------------------------------------------
    async def on_media(self, payload_b64: str) -> None:
        if self.ended:
            return  # audio still arriving after we hung up
        try:
            await self.stt.send_audio(base64.b64decode(payload_b64))
        except Exception as e:  # STT socket dropped: don't crash the call loop
            self.log.event("stt_send_error", error=type(e).__name__)

    async def on_mark(self, name: str) -> None:
        self.marks.discard(name)
        if not self.marks:
            self.playback_idle.set()
            self._arm_silence_timer()

    async def _send_audio(self, chunk: bytes) -> None:
        await self.twilio.send_text(json.dumps({
            "event": "media", "streamSid": self.stream_sid,
            "media": {"payload": base64.b64encode(chunk).decode()},
        }))

    async def _mark(self, label: str) -> None:
        self._mark_n += 1
        name = f"{label}-{self._mark_n}"
        self.marks.add(name)
        self.playback_idle.clear()
        await self.twilio.send_text(json.dumps({"event": "mark", "streamSid": self.stream_sid,
                                                "mark": {"name": name}}))

    def _first_audio(self, kind: str) -> None:
        t = self.turn
        if not t:
            return
        now = time.monotonic()
        if "first_audio_at" not in t:
            t["first_audio_at"], t["first_audio_kind"] = now, kind
        if kind == "answer" and "first_answer_at" not in t:
            t["first_answer_at"] = now

    async def _play(self, audio: bytes, label: str) -> None:
        self._cancel_silence_timer()
        self._first_audio("filler" if label.startswith("filler") else label)
        await self._send_audio(audio)
        await self._mark(label)

    async def _speak(self, text: str) -> None:
        self._cancel_silence_timer()
        t_req = time.monotonic()
        first = True
        async for chunk in self.tts.stream(text):
            if first:
                if self.turn is not None:
                    self.turn["tts_ttfb_ms"] = round((time.monotonic() - t_req) * 1000)
                self._first_audio("answer")
                first = False
            await self._send_audio(chunk)
        await self._mark("answer")

    # ---- caller turns -----------------------------------------------------
    async def _on_speech(self) -> None:
        self._cancel_silence_timer()

    async def _on_final(self, text: str, info: dict) -> None:
        if self.ended:
            return
        info["eot_at"] = time.monotonic()
        self.pending.append((text, info))
        self.reprompts = 0
        if not self.busy:
            self.busy = True
            asyncio.create_task(self._process())

    async def _process(self) -> None:
        try:
            while self.pending and not self.ended:
                # Caller spoke again before we answered: treat it as one turn.
                batch, self.pending = self.pending, []
                text = " ".join(t for t, _ in batch)
                info = batch[-1][1]
                self.turn = {"eot_at": info["eot_at"], "stt_endpoint_ms": info.get("stt_endpoint_ms")}
                self.log.event("stt_final", text=text, **{k: v for k, v in info.items() if k != "eot_at"})

                reply = await asyncio.to_thread(self.agent.handle_turn, text)
                self.turn["agent_ms"] = reply.latency_ms
                await self._speak(reply.text)
                self._record_turn()
                if reply.ended:
                    await self._hang_up("transfer" if reply.handoff else "agent_ended")
                    return
        finally:
            self.busy = False

    def _record_turn(self) -> None:
        t, eot = self.turn, self.turn["eot_at"]
        m = {
            "stt_endpoint_ms": t.get("stt_endpoint_ms"),
            "agent_ms": t.get("agent_ms"),
            "tts_ttfb_ms": t.get("tts_ttfb_ms"),
            "first_audio_ms": round((t["first_audio_at"] - eot) * 1000) if "first_audio_at" in t else None,
            "first_answer_audio_ms": round((t["first_answer_at"] - eot) * 1000) if "first_answer_at" in t else None,
            "filler": t.get("first_audio_kind") == "filler",
        }
        # What the caller feels: from the end of their speech to the first sound back.
        if m["stt_endpoint_ms"] is not None and m["first_audio_ms"] is not None:
            m["ttfa_ms"] = m["stt_endpoint_ms"] + m["first_audio_ms"]
            m["ttfa_answer_ms"] = m["stt_endpoint_ms"] + m["first_answer_audio_ms"]
        self.turn_metrics.append(m)
        self.log.event("voice_turn", **m)
        self.turn = None

    def _on_tool_start(self, tool_names: list[str]) -> None:
        """Called from the agent thread when a tool round starts: play a filler line right away."""
        if not set(tool_names) & (LOOKUP_TOOLS | WRITE_TOOLS):
            return  # end_call / transfer carry their own line
        key = "filler_write" if set(tool_names) & WRITE_TOOLS else "filler_lookup"
        asyncio.run_coroutine_threadsafe(self._play(_phrase_audio[key], key), self.loop)

    # ---- silence handling -------------------------------------------------
    def _arm_silence_timer(self) -> None:
        if self.ended or self.busy or self.pending:
            return
        self._cancel_silence_timer()
        self.silence_task = asyncio.create_task(self._silence_watch())

    def _cancel_silence_timer(self) -> None:
        if self.silence_task and not self.silence_task.done():
            self.silence_task.cancel()
        self.silence_task = None

    async def _silence_watch(self) -> None:
        try:
            await asyncio.sleep(SILENCE_REPROMPT_S)
        except asyncio.CancelledError:
            return
        if self.busy or self.ended:
            return
        if self.reprompts == 0:
            self.reprompts = 1
            self.log.event("silence_reprompt")
            self.silence_task = None
            await self._play(_phrase_audio["reprompt"], "reprompt")
        else:
            self.log.event("silence_hangup")
            self.ended = True
            self.agent.state.ended = True
            self.agent.state.end_reason = "end:no_response"
            self.silence_task = None
            await self._play(_phrase_audio["silence_bye"], "silence_bye")
            await self._hang_up("silence")

    async def _hang_up(self, reason: str) -> None:
        self.ended = True
        try:
            await asyncio.wait_for(self.playback_idle.wait(), timeout=30)  # let the last line finish
        except asyncio.TimeoutError:
            pass
        await self.close(reason)
        try:
            await self.twilio.close()  # ends the <Connect><Stream>; nothing follows it in TwiML, so the call ends
        except Exception:
            pass
