"""One phone call: Twilio media stream <-> STT <-> Agent <-> TTS.

The agent is the same object the text CLI uses; this file only adds what a
phone line needs:
  - streaming: Claude's text goes to Cartesia sentence by sentence as it's written
  - a filler line while tools run, and instant pre-synthesized fixed lines
  - barge-in: when the caller talks over the agent, playback stops and the agent
    is told what the caller actually heard
  - silence reprompt, hang-up, and a real transfer to a person with a spoken summary
  - time-to-first-audio measurement per turn
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import statistics
import time
import uuid
from typing import Any
from xml.sax.saxutils import escape, quoteattr

import hashlib
import hmac

from bookly import db
from bookly.agent import GREETING, Agent
from bookly.voice.stt import STTStream
from bookly.voice.tts import TTS

SILENCE_REPROMPT_S = 8.0
BARGE_IN_MIN_WORDS = 2          # a cough or "mm" shouldn't cut the agent off
LOOKUP_TOOLS = {"lookup_customer", "lookup_order", "search_faq", "verify_zip", "send_confirmation"}
WRITE_TOOLS = {"cancel_order", "start_return", "issue_store_credit", "send_password_reset"}
SENTENCE_END = re.compile(r"[.!?](?=\s)|\n")

PHRASES = {
    "greeting": GREETING,
    "filler_lookup": "Let me pull that up.",
    "filler_write": "One moment while I take care of that.",
    "filler_transfer": "Okay, one moment.",
    "reprompt": "Are you still there?",
    "silence_bye": "I haven't heard anything, so I'll end the call now. Thanks for calling Bookly. Goodbye.",
    "tts_down": "I'm sorry, I'm having trouble with my voice line right now. Please call back in a few minutes. Goodbye.",
}
_phrase_audio: dict[str, bytes] = {}

# Handoff packets waiting for the human to pick up (read by the /whisper webhook).
HANDOFFS: dict[str, dict[str, Any]] = {}

REASON_WORDS = {
    "angry_or_repeat_caller": "an upset or repeat caller",
    "lost_or_damaged": "a lost or damaged order",
    "outside_policy": "a request outside policy",
    "unclear_intent": "a request the assistant couldn't pin down",
    "faq_not_found": "a question the FAQ doesn't cover",
    "verification_failed": "failed verification",
    "caller_requested": "the caller asked for a person",
    "other": "an issue the assistant couldn't handle",
}


def whisper_twiml(packet: dict[str, Any]) -> str:
    """What the human hears before the caller is connected, so the caller never repeats themselves."""
    c = packet.get("customer") or {}
    via = packet.get("identified_via")
    who = (f"{c['name']}, identified by {via.replace('_', ' ')}." if c.get("name") and via
           else "Caller not identified.")
    order = packet.get("selected_order")
    wants = (packet.get("caller_wants") or "not stated").rstrip(".")
    parts = [
        f"Bookly A I transfer. {who}",
        f"Reason: {REASON_WORDS.get(packet.get('reason'), packet.get('reason', ''))}.",
        f"They want: {wants}.",
        (f"Order {' '.join(order)}." if order else ""),
        f"Summary: {packet.get('summary', '')}",
        "Connecting now.",
    ]
    return f'<?xml version="1.0" encoding="UTF-8"?><Response><Say>{escape(" ".join(p for p in parts if p))}</Say></Response>'


async def load_phrases() -> None:
    """Pre-synthesize fixed lines once so they play instantly (zero TTS latency)."""
    if _phrase_audio:
        return
    tts = TTS()
    await tts.start()
    try:
        for key, text in PHRASES.items():
            try:
                _phrase_audio[key] = await tts.synth(text)
            except Exception as e:  # keep serving: a missing fixed line is skipped, not fatal
                if key == "greeting":
                    raise
                print(f"[server] could not pre-synthesize {key!r}: {e}")
    finally:
        await tts.close()


def stream_token(call_sid: str, caller: str) -> str:
    """Binds a media stream to the call /voice answered. /voice only answers Twilio-signed requests, so
    only Twilio (or someone holding the auth token, e.g. the local loopback tester) can open /media
    with a given caller ID."""
    key = os.environ.get("TWILIO_AUTH_TOKEN", "").encode()
    return hmac.new(key, f"{call_sid}|{caller}".encode(), hashlib.sha256).hexdigest()


def e164(number: str) -> str:
    """'9805551234' / '1-980-555-1234' / '+19805551234' -> '+19805551234' (US default)."""
    n = (number or "").strip()
    if n.startswith("+"):
        return "+" + re.sub(r"\D", "", n)
    d = re.sub(r"\D", "", n)
    if len(d) == 10:
        return "+1" + d
    if len(d) == 11 and d.startswith("1"):
        return "+" + d
    return n


def _p50(xs: list[int]) -> int | None:
    return int(statistics.median(xs)) if xs else None


class CallSession:
    def __init__(self, twilio_ws, stream_sid: str, call_sid: str, caller: str | None):
        self.twilio = twilio_ws
        self.stream_sid, self.call_sid = stream_sid, call_sid
        self.loop = asyncio.get_running_loop()
        self.streaming = os.environ.get("VOICE_STREAMING", "1") == "1"
        self.barge_in = os.environ.get("VOICE_BARGE_IN", "1") == "1"
        self.agent = Agent(caller_id=caller, call_id=f"call-{call_sid[-10:]}", on_tool_start=self._on_tool_start)
        self.log = self.agent.log
        conn = db.connect()
        self.stt = STTStream(db.catalog_titles(conn) + ["Bookly"], on_final=self._on_final,
                             on_speech=self._on_speech, on_partial=self._on_partial)
        conn.close()
        self.tts = TTS()

        self.pending: list[tuple[str, dict]] = []
        self.busy = False
        self.ended = False
        self.marks: dict[str, str] = {}       # outstanding mark name -> text it ends
        self.heard: list[str] = []            # sentences the caller fully heard this turn
        self.playback_idle = asyncio.Event()
        self.playback_idle.set()
        self.silence_task: asyncio.Task | None = None
        self.reprompts = 0
        self.turn: dict[str, Any] | None = None
        self.turn_metrics: list[dict[str, Any]] = []
        self.interrupted = False              # current turn was cut off by the caller
        self.tts_ctx: str | None = None       # Cartesia context currently generating
        self.barge_ins = 0
        self.tts_failed = False
        self._mark_n = 0

    # ---- lifecycle --------------------------------------------------------
    async def start(self) -> None:
        self.log.event("phone_call_start", call_sid=self.call_sid, stream_sid=self.stream_sid,
                       streaming=self.streaming, barge_in=self.barge_in)
        await asyncio.gather(self.stt.start(), self.tts.start())
        self.agent.greeting()
        await self._play(_phrase_audio["greeting"], "greeting", PHRASES["greeting"])

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
            "barge_ins": self.barge_ins, "reprompts": self.reprompts, "close_reason": reason,
            "streaming": self.streaming, "stt_partials": self.stt.partials,
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
        text = self.marks.pop(name, None)
        if text is not None and name.startswith("s-"):
            self.heard.append(text)
        if not self.marks:
            self.playback_idle.set()
            self._arm_silence_timer()

    async def _send_audio(self, chunk: bytes) -> None:
        await self.twilio.send_text(json.dumps({
            "event": "media", "streamSid": self.stream_sid,
            "media": {"payload": base64.b64encode(chunk).decode()},
        }))

    async def _mark(self, label: str, text: str = "") -> None:
        self._mark_n += 1
        name = f"{label}-{self._mark_n}"
        self.marks[name] = text
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

    async def _play(self, audio: bytes, label: str, text: str = "") -> None:
        self._cancel_silence_timer()
        self._first_audio("filler" if label.startswith("filler") else label)
        await self._send_audio(audio)
        await self._mark(label, text)

    async def _say_sentence(self, text: str) -> None:
        """Synthesize one sentence and send its audio as it arrives."""
        if self.interrupted or not text.strip():
            return
        self._cancel_silence_timer()
        if self.tts_failed:
            return
        ctx = self.tts_ctx = uuid.uuid4().hex
        t_req = time.monotonic()
        first = True
        try:
            async for chunk in self.tts.stream(text, ctx=ctx):
                if self.interrupted:
                    break
                if first:
                    if self.turn is not None and "tts_ttfb_ms" not in self.turn:
                        self.turn["tts_ttfb_ms"] = round((time.monotonic() - t_req) * 1000)
                    self._first_audio("answer")
                    first = False
                await self._send_audio(chunk)
        except Exception as e:  # e.g. TTS credits or outage: never leave the caller in silence
            self.tts_failed = True
            self.tts_ctx = None
            self.log.event("tts_error", error=type(e).__name__, message=str(e)[:300])
            print(f"[tts error] {self.agent.call_id}: {str(e)[:160]}")
            return
        self.tts_ctx = None
        if not self.interrupted:
            await self._mark("s", text)

    async def _speaker(self, q: asyncio.Queue) -> None:
        """Turn a stream of text deltas into spoken sentences, in order."""
        buf = ""
        while True:
            item = await q.get()
            if item is None:
                if buf.strip():
                    await self._say_sentence(buf.strip())
                return
            if self.interrupted:
                continue  # caller cut us off: drop the rest of this reply
            buf += item
            while (m := SENTENCE_END.search(buf)):
                sentence, buf = buf[:m.end()].strip(), buf[m.end():]
                await self._say_sentence(sentence)

    # ---- barge-in ---------------------------------------------------------
    @property
    def agent_audible(self) -> bool:
        return bool(self.marks) or self.tts_ctx is not None

    async def _on_partial(self, transcript: str) -> None:
        if not self.barge_in or self.ended or not self.agent_audible:
            return
        if len(transcript.split()) < BARGE_IN_MIN_WORDS:
            return
        await self._interrupt(transcript)

    async def _interrupt(self, transcript: str) -> None:
        self.barge_ins += 1
        self.interrupted = self.busy  # drop the rest of the in-flight reply, if any
        cut = [t for t in self.marks.values() if t]
        await self.twilio.send_text(json.dumps({"event": "clear", "streamSid": self.stream_sid}))
        if self.tts_ctx:
            await self.tts.cancel(self.tts_ctx)
        self.marks.clear()
        self.playback_idle.set()
        heard = " ".join(self.heard).strip()
        st = self.agent.state
        readback_cut = bool(cut) and st.pending_action is not None and st.pending_action.proposed_at_turn == st.caller_turns
        if readback_cut:
            st.pending_action = None  # they never heard the whole read-back, so nothing they say next confirms it
        st.interruption_note = (
            "The caller interrupted your last reply. "
            + (f'They heard: "{heard}". ' if heard else "They heard almost none of it. ")
            + (f'They did not hear: "{" ".join(cut)}". ' if cut else "")
            + ("Your read-back was cut off, so the change is NOT confirmed: read it back again if they still want it. "
               if readback_cut else "")
            + "Respond to what they just said; repeat anything important they missed only if it's still relevant."
        )
        self.log.event("barge_in", partial=transcript, heard=heard, cut=cut)

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
                self.interrupted = False
                self.heard = []
                self.log.event("stt_final", text=text, **{k: v for k, v in info.items() if k != "eot_at"})

                q: asyncio.Queue = asyncio.Queue()
                speaker = asyncio.create_task(self._speaker(q))
                on_text = (lambda t: self.loop.call_soon_threadsafe(q.put_nowait, t)) if self.streaming else None
                reply = await asyncio.to_thread(self.agent.handle_turn, text, on_text)
                self.turn["agent_ms"] = reply.latency_ms
                if not self.streaming:
                    q.put_nowait(reply.text + "\n")
                q.put_nowait(None)
                await speaker
                self._record_turn()
                if self.tts_failed:
                    # Can't speak answers: say the pre-made line (if we have it) and end cleanly.
                    if "tts_down" in _phrase_audio:
                        await self._play(_phrase_audio["tts_down"], "tts_down", PHRASES["tts_down"])
                    self.agent.state.end_reason = self.agent.state.end_reason or "end:tts_error"
                    await self._hang_up("tts_error")
                    return
                if reply.ended:
                    await self._finish(reply)
                    return
        finally:
            self.busy = False
            if not self.marks:
                self._arm_silence_timer()

    def _record_turn(self) -> None:
        t, eot = self.turn, self.turn["eot_at"]
        m = {
            "stt_endpoint_ms": t.get("stt_endpoint_ms"),
            "agent_ms": t.get("agent_ms"),
            "tts_ttfb_ms": t.get("tts_ttfb_ms"),
            "first_audio_ms": round((t["first_audio_at"] - eot) * 1000) if "first_audio_at" in t else None,
            "first_answer_audio_ms": round((t["first_answer_at"] - eot) * 1000) if "first_answer_at" in t else None,
            "filler": t.get("first_audio_kind") == "filler",
            "streaming": self.streaming,
            "interrupted": self.interrupted,
        }
        # What the caller feels: from the end of their speech to the first sound back.
        if m["stt_endpoint_ms"] is not None and m["first_audio_ms"] is not None:
            m["ttfa_ms"] = m["stt_endpoint_ms"] + m["first_audio_ms"]
            m["ttfa_answer_ms"] = m["stt_endpoint_ms"] + (m["first_answer_audio_ms"] or m["first_audio_ms"])
        self.turn_metrics.append(m)
        self.log.event("voice_turn", **m)
        self.turn = None

    def _on_tool_start(self, tool_names: list[str]) -> None:
        """Called from the agent thread when a tool round starts: play a filler line right away,
        unless the caller is already hearing something this turn."""
        names = set(tool_names)
        if names & WRITE_TOOLS:
            key = "filler_write"
        elif names & LOOKUP_TOOLS:
            key = "filler_lookup"
        elif "transfer_to_human" in names:
            key = "filler_transfer"  # the model is still writing the handoff summary
        else:
            return  # end_call: its goodbye comes right away

        async def maybe_play():
            if self.turn is not None and "first_audio_at" not in self.turn and not self.interrupted:
                await self._play(_phrase_audio[key], key)
        asyncio.run_coroutine_threadsafe(maybe_play(), self.loop)

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
            await self._play(_phrase_audio["reprompt"], "reprompt", PHRASES["reprompt"])
        else:
            self.log.event("silence_hangup")
            self.ended = True
            self.agent.state.ended = True
            self.agent.state.end_reason = "end:no_response"
            self.silence_task = None
            await self._play(_phrase_audio["silence_bye"], "silence_bye", PHRASES["silence_bye"])
            await self._hang_up("silence")

    # ---- ending: hang up or hand off --------------------------------------
    async def _finish(self, reply) -> None:
        if reply.handoff and os.environ.get("TRANSFER_NUMBER", "").strip():
            await self._transfer(reply.handoff)
        else:
            await self._hang_up("transfer_unconfigured" if reply.handoff else "agent_ended")

    async def _wait_playback(self) -> None:
        try:
            await asyncio.wait_for(self.playback_idle.wait(), timeout=30)  # let the last line finish
        except asyncio.TimeoutError:
            pass

    async def _transfer(self, packet: dict[str, Any]) -> None:
        """Real handoff: redirect the live call to a person. The person first hears a whisper
        with the structured summary, then the caller is connected."""
        self.ended = True
        await self._wait_playback()
        HANDOFFS[self.call_sid] = packet
        host = os.environ["PUBLIC_HOST"].strip()
        bookly = os.environ.get("TWILIO_PHONE_NUMBER", "")
        to = e164(os.environ["TRANSFER_NUMBER"])
        whisper = f"https://{host}/whisper?call={self.call_sid}"
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?><Response>'
            f'<Dial callerId={quoteattr(bookly)} timeout="25"><Number url={quoteattr(whisper)}>{escape(to)}</Number></Dial>'
            "<Say>Sorry, no specialist is available right now. We'll call you back soon. Goodbye.</Say>"
            "</Response>"
        )

        def redirect():
            from twilio.rest import Client
            Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"]).calls(self.call_sid).update(
                twiml=twiml)

        try:
            await asyncio.to_thread(redirect)
            self.log.event("transfer_dialed", to_last4=to[-4:], reason=packet.get("reason"))
            print(f"[transfer] {self.agent.call_id} dialing ...{to[-4:]} reason={packet.get('reason')}")
            await self.close("transferred")  # Twilio ends the media stream when the call is redirected
        except Exception as e:
            self.log.event("transfer_error", error=type(e).__name__, message=str(e)[:300])
            print(f"[transfer error] {type(e).__name__}: {str(e)[:200]}")
            await self._hang_up("transfer_failed")

    async def _hang_up(self, reason: str) -> None:
        self.ended = True
        await self._wait_playback()
        await self.close(reason)
        try:
            await self.twilio.close()  # ends the <Connect><Stream>; nothing follows it in TwiML, so the call ends
        except Exception:
            pass
