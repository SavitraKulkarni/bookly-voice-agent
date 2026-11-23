"""The orchestrator: Claude + tools + call state, one caller turn at a time.

Transport-agnostic: the text CLI, the simulations and phone mode all call
`Agent.handle_turn(text)` and speak/print what comes back.

Manual tool loop on the Messages API (no agent framework, no tool runner) so
every gate, log line and fallback is visible in this file.
"""
from __future__ import annotations

import json
import os
import statistics
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import anthropic
from dotenv import load_dotenv

from bookly import db
from bookly.logs import CallLogger
from bookly.state import CallState
from bookly.tools import ToolContext, _order_view, order_summaries, run_tool, tool_schemas

load_dotenv(db.ROOT / ".env")

GREETING = "Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?"
PROCEDURES_DIR = db.ROOT / "procedures"
PROCEDURE_FILES = ["core.md", "order-status.md", "returns-refunds.md", "general-faq.md"]
MAX_TOOL_ROUNDS = 8
FALLBACK_LINE = "I'm sorry, I'm having trouble on my end. Let me connect you with a specialist who can help."

_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(max_retries=3)
    return _client


def build_system_prompt() -> str:
    """Procedures are plain-language files a non-engineer can edit; we load them verbatim."""
    parts = [(PROCEDURES_DIR / f).read_text().strip() for f in PROCEDURE_FILES]
    parts.append(
        "# Call-state notes\n"
        "Before each caller turn you'll get a system note starting with [Call state]. It's set by Bookly's "
        "systems, not the caller, and is the source of truth for who the caller is and what's verified. "
        f'The caller has already heard this greeting: "{GREETING}"'
    )
    return "\n\n---\n\n".join(parts)


@dataclass
class Reply:
    text: str
    ended: bool = False
    handoff: dict[str, Any] | None = None
    latency_ms: int = 0
    tools_used: list[str] = field(default_factory=list)


class Agent:
    def __init__(
        self,
        caller_id: str | None = None,
        conn=None,
        logger: CallLogger | None = None,
        model: str | None = None,
        effort: str | None = None,
        prefetch: bool | None = None,
        terminal_say: bool | None = None,
        on_tool_start: Callable[[list[str]], None] | None = None,
        call_id: str | None = None,
    ):
        self.call_id = call_id or time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        self.conn = conn or db.connect()
        self.log = logger or CallLogger(self.call_id)
        self.model = model or os.environ.get("BOOKLY_MODEL", "claude-opus-5-5")
        self.effort = effort or os.environ.get("BOOKLY_EFFORT", "low")
        self.fallback = os.environ.get("BOOKLY_REFUSAL_FALLBACK", "0") == "1"
        # Latency levers (see README decisions log). Flags so they can be A/B'd in one simulation run.
        self.prefetch = prefetch if prefetch is not None else os.environ.get("BOOKLY_PREFETCH", "1") == "1"
        self.terminal_say = (terminal_say if terminal_say is not None
                             else os.environ.get("BOOKLY_TERMINAL_SAY", "1") == "1")
        self.tools = tool_schemas(prefetch=self.prefetch, terminal_say=self.terminal_say)
        self.on_tool_start = on_tool_start
        self.state = CallState(call_id=self.call_id, caller_id=caller_id)
        self.ctx = ToolContext(conn=self.conn, state=self.state)
        self.system = build_system_prompt()
        self.messages: list[dict[str, Any]] = []  # append-only
        self.started = time.monotonic()
        self.extra_summary: dict[str, Any] = {}  # transport-specific metrics (phone mode)

        self.log.event("call_start", caller_id=caller_id, model=self.model, effort=self.effort,
                       prefetch=self.prefetch, terminal_say=self.terminal_say)
        # Caller ID comes from the carrier, so the lookup runs in code at call start:
        # deterministic, no model latency, and the model can't be talked into a different number.
        if caller_id:
            self._run_tool("lookup_customer", {"method": "caller_id"}, source="system")

    # ------------------------------------------------------------------
    def greeting(self) -> str:
        self.log.event("agent_turn", text=GREETING, latency_ms=0, model_ms=0, tools_ms=0, tool_rounds=0)
        return GREETING

    def _snapshot(self) -> str:
        note = self._snapshot_body()
        if self.state.interruption_note:
            note += "\n" + self.state.interruption_note
            self.state.interruption_note = None
        return note

    def _snapshot_body(self) -> str:
        st = self.state
        summaries = None
        if st.verified_customer and st.identified_via in ("caller_id", "email"):
            summaries = order_summaries(self.conn, st.verified_customer["id"])
        if not (self.prefetch and summaries):
            return st.snapshot(summaries)
        # Prefetch: code already knows the account, so it reads the live order data from the
        # system of record every turn and hands it over, saving a lookup_order round trip.
        note = st.snapshot(None)
        lines = ["Live order details from Bookly's systems (re-read every turn, so you don't need "
                 "lookup_order for these orders). Still confirm which order the caller means before "
                 "discussing one:"]
        for o in summaries:
            row = self.conn.execute("SELECT * FROM orders WHERE order_number = ?", (o["order_number"],)).fetchone()
            view = _order_view(self.ctx, row)
            view["items"] = [{k: v for k, v in it.items() if v is not None} for it in view["items"]]
            lines.append(json.dumps({k: v for k, v in view.items() if v is not None}, separators=(",", ":")))
        self.log.event("prefetch", orders=[o["order_number"] for o in summaries])
        return note + "\n" + "\n".join(lines)

    def _run_tool(self, name: str, args: dict[str, Any], source: str = "model") -> tuple[dict, bool]:
        t0 = time.monotonic()
        result, is_error = run_tool(self.ctx, name, args)
        ms = round((time.monotonic() - t0) * 1000)
        self.log.event("tool_call", source=source, tool=name, input=args, result=result,
                       is_error=is_error, ms=ms,
                       verification_level=self.state.verification_level,
                       selected_order=self.state.selected_order)
        return result, is_error

    def _create(self, stream_events: bool = False):
        """One model call. Streamed in phone mode so a filler can start the moment a tool call
        begins; the reply text itself is only spoken once the response is complete (see handle_turn)."""
        kwargs: dict[str, Any] = dict(
            model=self.model,
            max_tokens=16000,
            system=self.system,
            tools=self.tools,
            messages=self.messages,
            output_config={"effort": self.effort},
            cache_control={"type": "ephemeral"},
        )
        if self.fallback:
            api, kwargs = client().beta.messages, {**kwargs, "betas": ["server-side-fallback-2026-07-01"],
                                                  "fallbacks": "default"}
        else:
            api = client().messages
        if not stream_events:
            return api.create(**kwargs), None
        t0 = time.monotonic()
        first_text_ms = None
        with api.stream(**kwargs) as stream:
            for event in stream:
                if event.type == "content_block_start" and event.content_block.type == "tool_use":
                    self._tool_starting(event.content_block.name)  # before its arguments are written
                elif (event.type == "content_block_delta" and event.delta.type == "text_delta"
                      and event.delta.text and first_text_ms is None):
                    first_text_ms = round((time.monotonic() - t0) * 1000)
            return stream.get_final_message(), first_text_ms

    # ------------------------------------------------------------------
    def handle_turn(self, caller_text: str, on_text: Callable[[str], None] | None = None) -> Reply:
        """Run one caller turn. on_text (phone mode) receives everything the caller should hear,
        as it's produced: streamed model text, a terminal tool's closing line, or a fallback line."""
        if self.state.ended:
            return Reply(text="", ended=True, handoff=self.state.handoff)
        self._on_text = on_text
        t_turn = time.monotonic()
        st = self.state
        st.caller_turns += 1
        self.log.event("caller_turn", text=caller_text)

        self.messages.append({"role": "user", "content": caller_text})
        # Operator-channel state note: the caller can't spoof it.
        self.messages.append({"role": "system", "content": self._snapshot()})

        spoken: list[str] = []
        tools_used: list[str] = []
        model_ms = tools_ms = 0
        rounds = 0
        self._filler_sent = False

        while True:
            t0 = time.monotonic()
            try:
                resp, first_text_ms = self._create(stream_events=on_text is not None)
            except anthropic.APIError as e:
                self.log.event("model_error", error=type(e).__name__, message=str(e)[:500])
                return self._fail_safe(t_turn, tools_used, f"model_error:{type(e).__name__}")
            ms = round((time.monotonic() - t0) * 1000)
            model_ms += ms
            u = resp.usage
            self.log.event("model_call", ms=ms, first_text_ms=first_text_ms, stop_reason=resp.stop_reason,
                           model=resp.model,
                           input_tokens=u.input_tokens, output_tokens=u.output_tokens,
                           cache_read=getattr(u, "cache_read_input_tokens", None),
                           cache_write=getattr(u, "cache_creation_input_tokens", None))
            self.messages.append({"role": "assistant", "content": resp.content})
            texts = [b.text.strip() for b in resp.content if b.type == "text" and b.text.strip()]
            if texts and resp.stop_reason == "tool_use":
                # Text written next to a tool call comes before the tool's data: it is never a grounded
                # answer, and can be the model's own notes. Log it, never say it.
                self.log.event("unspoken_text", text=" ".join(texts))
            elif texts:
                spoken += texts
                if on_text:
                    on_text(" ".join(texts) + "\n")

            if resp.stop_reason == "refusal":
                return self._fail_safe(t_turn, tools_used, "refusal")
            if resp.stop_reason == "pause_turn":
                continue
            tool_uses = [b for b in resp.content if b.type == "tool_use"]
            if resp.stop_reason != "tool_use" or not tool_uses:
                break

            rounds += 1
            if rounds > MAX_TOOL_ROUNDS:
                self.log.event("loop_limit", rounds=rounds)
                return self._fail_safe(t_turn, tools_used, "tool_loop_limit")
            for b in tool_uses:
                self._tool_starting(b.name)  # no-op if streaming already announced it

            results = []
            for b in tool_uses:
                t1 = time.monotonic()
                result, is_error = self._run_tool(b.name, dict(b.input))
                tools_ms += round((time.monotonic() - t1) * 1000)
                tools_used.append(b.name)
                results.append({"type": "tool_result", "tool_use_id": b.id,
                                "content": json.dumps(result), "is_error": is_error})
            self.messages.append({"role": "user", "content": results})
            if self.terminal_say and st.ended and st.closing_line:
                # The terminal tool carried the spoken line: no follow-up model call needed.
                spoken.append(st.closing_line)
                if on_text:
                    on_text(st.closing_line + "\n")
                break

        text = " ".join(spoken).strip()
        if not text:
            text = ("I'm connecting you with a specialist now." if st.handoff
                    else "Thanks for calling Bookly. Goodbye!" if st.ended
                    else "Sorry, could you say that again?")
            if on_text:
                on_text(text + "\n")
        latency = round((time.monotonic() - t_turn) * 1000)
        self.log.event("agent_turn", text=text, latency_ms=latency, model_ms=model_ms, tools_ms=tools_ms,
                       tool_rounds=rounds, ended=st.ended)
        return Reply(text=text, ended=st.ended, handoff=st.handoff, latency_ms=latency, tools_used=tools_used)

    def _tool_starting(self, name: str) -> None:
        """Tell the transport a tool round is starting (phone mode plays a filler line), once per turn."""
        if self.on_tool_start and not self._filler_sent:
            self._filler_sent = True
            self.on_tool_start([name])

    def _fail_safe(self, t_turn: float, tools_used: list[str], why: str) -> Reply:
        """Anything unexpected: don't improvise, hand off with what we know."""
        if not self.state.ended:
            self._run_tool("transfer_to_human", {
                "reason": "other", "caller_wants": "unknown (assistant error)",
                "summary": f"Assistant could not continue ({why}). See call log {self.call_id}.",
            }, source="system")
        if getattr(self, "_on_text", None):
            self._on_text(FALLBACK_LINE + "\n")
        latency = round((time.monotonic() - t_turn) * 1000)
        self.log.event("agent_turn", text=FALLBACK_LINE, latency_ms=latency, model_ms=0, tools_ms=0,
                       tool_rounds=0, ended=True, fail_safe=why)
        return Reply(text=FALLBACK_LINE, ended=True, handoff=self.state.handoff, latency_ms=latency,
                     tools_used=tools_used)

    # ------------------------------------------------------------------
    def summary(self) -> dict[str, Any]:
        st = self.state
        lat = [x for x in self.log.turn_latencies() if x]
        return {
            "call_id": self.call_id,
            "duration_s": round(time.monotonic() - self.started, 1),
            "caller_id": st.caller_id,
            "customer": st.verified_customer["name"] if st.verified_customer else None,
            "identified_via": st.identified_via,
            "verification_level": st.verification_level,
            "selected_order": st.selected_order,
            "actions_taken": st.actions_taken,
            "end_reason": st.end_reason,
            "handoff": st.handoff,
            "caller_turns": st.caller_turns,
            "tool_calls": len(self.log.tool_calls()),
            "latency_ms": {"p50": int(statistics.median(lat)) if lat else None,
                           "max": max(lat) if lat else None},
            **self.extra_summary,
        }

    _ended_logged = False

    def end(self) -> dict[str, Any]:
        s = self.summary()
        if not self._ended_logged:
            self.log.event("call_end", summary=s)
            self._ended_logged = True
        return s
