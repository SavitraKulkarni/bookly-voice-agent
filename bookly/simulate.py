"""Simulated calls: an LLM plays the caller, the real agent answers, and code checks the outcome.

    python -m bookly.simulate                  # all personas, in parallel
    python -m bookly.simulate --only angry_transfer

Each persona gets a fresh copy of the seeded DB. Pass/fail is decided by code
from the call log, the call state and the database (what the agent *did*),
not by asking a model whether the call went well.
Transcripts are written to docs/transcripts/.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from bookly import db
from bookly.agent import GREETING, Agent, client
from bookly.logs import CallLogger
from bookly.tools import WRITE_TOOLS
from data.seed import UNKNOWN_PHONE, seed

TRANSCRIPTS = db.ROOT / "docs" / "transcripts"
MAX_CALLER_TURNS = 14
HANGUP = "[HANGUP]"

CALLER_SYSTEM = """You are role-playing a customer phoning Bookly's support line, to test an AI phone agent. Stay in character.

Who you are and what you want:
{persona}

How to play it:
- Talk like a real person on the phone: one or two short sentences, casual. No stage directions, asterisks or emoji.
- Only give details (ZIP code, order number, email) when you're asked for them.
- Follow your script, but react naturally to what the agent actually says.
- When your goal is done, or you're told you're being transferred, say a brief goodbye.
- If the agent has already said goodbye or said it's transferring you, reply with exactly: [HANGUP]"""


# ---------------------------------------------------------------------------
@dataclass
class SimResult:
    persona: "Persona"
    agent: Agent
    log: CallLogger
    conn: Any
    error: str | None = None
    checks: list[tuple[str, bool, str]] = field(default_factory=list)

    # views over the call log ------------------------------------------------
    @property
    def events(self):
        return self.log.events

    def tool_calls(self, name: str | None = None, **match) -> list[dict]:
        out = []
        for e in self.log.tool_calls():
            if name and e["tool"] != name:
                continue
            if any(str(e["input"].get(k)) != str(v) for k, v in match.items()):
                continue
            out.append(e)
        return out

    def saw_order(self, num: str) -> bool:
        """Order data reached the agent from the system of record: a lookup_order call, or code prefetch."""
        return bool(self.ok_calls("lookup_order", order_number=num)) or any(
            e["event"] == "prefetch" and num in e["orders"] for e in self.events)

    def ok_calls(self, name: str, **match) -> list[dict]:
        return [e for e in self.tool_calls(name, **match) if not e["is_error"]]

    def agent_texts(self) -> list[str]:
        return [e["text"] for e in self.events if e["event"] == "agent_turn"][1:]  # skip greeting

    def index(self, pred: Callable[[dict], bool]) -> int:
        """Position of the first event matching pred (or a big number)."""
        for i, e in enumerate(self.events):
            if pred(e):
                return i
        return 10**9

    def executed_writes(self) -> list[dict]:
        done = {"cancelled", "return_started", "credit_issued", "sent"}
        return [e for e in self.log.tool_calls()
                if e["tool"] in WRITE_TOOLS and not e["is_error"] and e["result"].get("status") in done]


def mentions(text: str, *words: str) -> bool:
    t = text.lower()
    return any(w.lower() in t for w in words)


# ---------------------------------------------------------------------------
@dataclass
class Persona:
    id: str
    title: str
    caller_id: str | None
    caller_name: str
    shows: str
    script: str
    checks: list[tuple[str, Callable[[SimResult], bool]]]


def _is_agent_turn_with_question(r: SimResult, n: int) -> bool:
    texts = r.agent_texts()
    return len(texts) > n and "?" in texts[n]


PERSONAS: list[Persona] = [
    Persona(
        id="happy_path",
        title="Happy path: order status + tracking text",
        caller_id="+13125550142",
        caller_name="James Okafor",
        shows="multi-turn, tool use (lookup_order, send_confirmation), caller-ID identification",
        script="You're James Okafor. You ordered Project Hail Mary by Andy Weir a few days ago and want to know "
               "when it'll arrive. After you hear, ask them to text you the tracking number. Then say thanks, "
               "that's all.",
        checks=[
            ("identified by caller ID at call start",
             lambda r: r.tool_calls("lookup_customer")[0]["result"].get("found") is True),
            ("order 419120 data from the system", lambda r: r.saw_order("419120")),
            ("status given from data (shipped)", lambda r: any(mentions(t, "ship", "on its way", "on the way")
                                                                for t in r.agent_texts())),
            ("tracking texted to caller ID", lambda r: any(
                c["result"].get("status") == "sent" for c in r.ok_calls("send_confirmation", kind="tracking"))),
            ("no writes, no transfer", lambda r: not r.executed_writes() and not r.agent.state.handoff),
        ],
    ),
    Persona(
        id="multi_book_clarify",
        title="Clarifying question: which order / which books",
        caller_id="+14155550101",
        caller_name="Maya Chen",
        shows="clarifying question before answering (3 orders, one with 2 books), title + author confirmed back",
        script="You're Maya Chen. Open with only: \"Hi, I'm calling to check on my order.\" Don't say which order. "
               "If asked which one, say: \"The one with two books in it. I think one was Klara and the Sun.\" "
               "Once you hear its status, say thanks and goodbye.",
        checks=[
            ("first reply is a question, not an answer", lambda r: _is_agent_turn_with_question(r, 0)),
            ("no order looked up before asking", lambda r: r.index(lambda e: e["event"] == "tool_call"
                                                                and e["tool"] == "lookup_order")
             > r.index(lambda e: e["event"] == "agent_turn" and e["latency_ms"] > 0 and "?" in e["text"])),
            ("question names the books to choose from", lambda r: sum(
                mentions(r.agent_texts()[0], w) for w in ("Klara", "Overstory", "Educated")) >= 2),
            ("talked about the right order (418027)", lambda r: r.saw_order("418027") and any(
                mentions(t, "4 1 8 0 2 7", "Klara", "Tomorrow", "Zevin") for t in r.agent_texts()[1:])),
            ("confirmed title + author back", lambda r: any(mentions(t, "Ishiguro") or mentions(t, "Zevin")
                                                            for t in r.agent_texts()[1:])),
            ("status given from data (delivered)", lambda r: any(mentions(t, "deliver") for t in r.agent_texts()[1:])),
            ("no writes, no transfer", lambda r: not r.executed_writes() and not r.agent.state.handoff),
        ],
    ),
    Persona(
        id="return_credit_declined",
        title="Return: store credit offered once, declined, refund issued",
        caller_id="+14155550101",
        caller_name="Maya Chen",
        shows="multi-turn info collection, ZIP step-up for writes, credit-first offer, read-back + confirm, "
              "idempotent write, receipt",
        script="You're Maya Chen. You want to return Klara and the Sun because you got it twice as a gift. You don't "
               "know the order number. Your ZIP is 94110 (only say it when asked). If they offer store credit, "
               "decline once: \"No thanks, I'd rather have a refund.\" Say yes when they read the return back to you. "
               "If they offer a receipt, ask for it by text. Then say thanks, bye.",
        checks=[
            ("ZIP verified before the return", lambda r: r.index(lambda e: e.get("tool") == "verify_zip"
                                                                 and e["result"].get("verified"))
             < r.index(lambda e: e.get("tool") == "start_return" and e["result"].get("status") == "return_started")),
            ("read-back before executing", lambda r: r.index(lambda e: e.get("tool") == "start_return"
                                                             and e["result"].get("status") == "needs_confirmation")
             < r.index(lambda e: e.get("tool") == "start_return" and e["result"].get("status") == "return_started")),
            ("store credit offered before refund", lambda r: r.index(lambda e: e["event"] == "agent_turn"
                                                                     and mentions(e["text"], "store credit"))
             < r.index(lambda e: e.get("tool") == "start_return" and e["result"].get("status") == "return_started")),
            ("credit offered only once", lambda r: sum(mentions(t, "store credit") and "?" in t
                                                       for t in r.agent_texts()) <= 1),
            ("refund recorded for Klara and the Sun (item 1)", lambda r: r.conn.execute(
                "SELECT COUNT(*) FROM returns WHERE item_id=1 AND resolution='refund'").fetchone()[0] == 1),
            ("no store credit issued", lambda r: not r.ok_calls("issue_store_credit")),
            ("receipt texted", lambda r: any(c["result"].get("status") == "sent"
                                             for c in r.ok_calls("send_confirmation", kind="receipt"))),
            ("no transfer", lambda r: not r.agent.state.handoff),
        ],
    ),
    Persona(
        id="outside_window",
        title="Return outside the 30-day window: state policy, no exception, hand off",
        caller_id="+12065550177",
        caller_name="Daniel Reyes",
        shows="policy stated without negotiating, escalation with structured handoff",
        script="You're Daniel Reyes. You want to return The Name of the Wind by Patrick Rothfuss; you didn't like "
               "it. Your ZIP is 98103 if asked. When told it's outside the return window, push back once: "
               "\"It's only a few weeks late, can't you make an exception?\" If offered a person, accept.",
        checks=[
            ("order 416881 data from the system", lambda r: r.saw_order("416881")),
            ("stated the 30-day policy", lambda r: any(mentions(t, "30", "thirty") for t in r.agent_texts())),
            ("no return created", lambda r: r.conn.execute("SELECT COUNT(*) FROM returns").fetchone()[0] == 0),
            ("transferred: outside_policy", lambda r: bool(r.agent.state.handoff)
             and r.agent.state.handoff["reason"] == "outside_policy"),
            ("handoff names the order", lambda r: bool(r.agent.state.handoff) and (
                r.agent.state.handoff.get("selected_order") == "416881")),
        ],
    ),
    Persona(
        id="unknown_caller",
        title="Unknown caller: order number, then ZIP to cancel a processing order",
        caller_id=UNKNOWN_PHONE,
        caller_name="Sofia Alvarez (calling from an unknown number)",
        shows="identity scales with risk (order number for read, + ZIP for write), processing → cancel",
        script="You're Sofia Alvarez, calling from a friend's phone. You want to know the status of your order of "
               "Lessons in Chemistry. When asked, your order number is 420044. When you hear it hasn't shipped, "
               "say you'd like to cancel it because you found it at a local shop. Your ZIP is 11215 if asked. Say yes "
               "to the read-back. If offered a receipt, yes, by email. Then bye.",
        checks=[
            ("caller ID didn't match", lambda r: r.tool_calls("lookup_customer")[0]["result"].get("found") is False),
            ("asked for order number", lambda r: mentions(r.agent_texts()[0], "order number")),
            ("identified by order number", lambda r: r.agent.state.identified_via == "order_number"),
            ("ZIP verified before cancelling", lambda r: r.index(lambda e: e.get("tool") == "verify_zip"
                                                                 and e["result"].get("verified"))
             < r.index(lambda e: e.get("tool") == "cancel_order" and e["result"].get("status") == "cancelled")),
            ("read-back before cancelling", lambda r: bool(r.tool_calls("cancel_order")) and
             r.tool_calls("cancel_order")[0]["result"].get("status") == "needs_confirmation"),
            ("order 420044 cancelled in DB", lambda r: r.conn.execute(
                "SELECT status FROM orders WHERE order_number='420044'").fetchone()[0] == "cancelled"),
            ("no transfer", lambda r: not r.agent.state.handoff),
        ],
    ),
    Persona(
        id="angry_transfer",
        title="Angry repeat caller with a lost order: immediate handoff",
        caller_id="+16175550188",
        caller_name="Robert Kim",
        shows="knowing when not to decide: escalation with a structured summary, no attempted fixes",
        script="You're Robert Kim and you're angry. Open with: \"This is the third time I'm calling. My book never "
               "showed up and nobody has fixed it!\" The book is The Covenant of Water. You want a real person. "
               "Don't calm down easily.",
        checks=[
            ("transferred", lambda r: bool(r.agent.state.handoff)),
            ("reason is angry/repeat or lost", lambda r: bool(r.agent.state.handoff) and
             r.agent.state.handoff["reason"] in ("angry_or_repeat_caller", "lost_or_damaged")),
            ("handed off within 2 replies", lambda r: len(r.agent_texts()) <= 2),
            ("no writes attempted", lambda r: not any(c["tool"] in WRITE_TOOLS for c in r.log.tool_calls())),
            ("handoff summary identifies the order/book", lambda r: bool(r.agent.state.handoff) and (
                r.agent.state.handoff.get("selected_order") == "415930"
                or mentions(r.agent.state.handoff["summary"] + r.agent.state.handoff["caller_wants"],
                            "415930", "Covenant"))),
        ],
    ),
]

from data.seed import ITEMS as _CATALOG

# Titles and authors must be read back (spec), so they don't count against the length limit.
_BOOK_NAMES = sorted({x for _, title, author, _, _ in _CATALOG for x in (title, author)}, key=len, reverse=True)


def _spoken_words(text: str) -> int:
    for name in _BOOK_NAMES:
        text = text.replace(name, " ")
    return len(text.split())


MARKDOWN = re.compile(r"(\*\*|^#|^\s*[-*•]\s|\[.*\]\(|https?://)", re.M)

GLOBAL_CHECKS: list[tuple[str, Callable[[SimResult], bool]]] = [
    ("greeting verbatim", lambda r: r.events and any(e["event"] == "agent_turn" and e["text"] == GREETING
                                                     for e in r.events[:3])),
    ("call ended cleanly (end_call or transfer)", lambda r: r.agent.state.ended),
    ("no malformed tool calls", lambda r: not any(c["result"].get("error") in ("bad_arguments", "unknown_tool")
                                                  for c in r.log.tool_calls())),
    ("voice style: replies <= 60 words (book titles/authors not counted), no markdown/URLs", lambda r: all(
        _spoken_words(t) <= 60 and not MARKDOWN.search(t) for t in r.agent_texts())),
]


# ---------------------------------------------------------------------------
def caller_reply(persona: Persona, convo: list[dict]) -> str:
    resp = client().messages.create(
        model=os.environ.get("BOOKLY_SIM_MODEL", "claude-opus-5-5"),
        max_tokens=2000,
        system=CALLER_SYSTEM.format(persona=persona.script),
        messages=convo,
        output_config={"effort": "low"},
    )
    return " ".join(b.text for b in resp.content if b.type == "text").strip()


def run_persona(p: Persona, run_dir: Path, tag: str = "", agent_kwargs: dict | None = None) -> SimResult:
    name = f"{p.id}{tag}"
    db_file = run_dir / f"{name}.db"
    seed(db_file)
    conn = db.connect(db_file)
    log = CallLogger(f"sim-{name}", log_dir=run_dir)
    agent = Agent(caller_id=p.caller_id, conn=conn, logger=log, call_id=f"sim-{name}", **(agent_kwargs or {}))
    r = SimResult(persona=p, agent=agent, log=log, conn=conn)
    try:
        convo = [{"role": "user", "content": agent.greeting()}]
        for _ in range(MAX_CALLER_TURNS):
            said = caller_reply(p, convo)
            if not said or said.strip() == HANGUP:
                log.event("caller_hangup")
                break
            said = said.replace(HANGUP, "").strip()
            convo.append({"role": "assistant", "content": said})
            reply = agent.handle_turn(said)
            convo.append({"role": "user", "content": reply.text})
            if reply.ended:
                break
    except Exception as e:  # keep other personas running; report it
        r.error = f"{type(e).__name__}: {e}"
        log.event("sim_error", error=r.error)
    agent.end()
    for name, fn in GLOBAL_CHECKS + p.checks:
        try:
            ok = bool(fn(r))
            r.checks.append((name, ok, ""))
        except Exception as e:
            r.checks.append((name, False, f"{type(e).__name__}: {e}"))
    if r.error:
        r.checks.append(("simulation ran without errors", False, r.error))
    return r


# ---------------------------------------------------------------------------
def _short(obj: Any, n: int = 220) -> str:
    s = json.dumps(obj)
    return s if len(s) <= n else s[:n] + "…"


def write_transcript(r: SimResult, out_dir: Path) -> Path:
    p, a = r.persona, r.agent
    passed = sum(ok for _, ok, _ in r.checks)
    summ = a.summary()
    lines = [
        f"# {p.title}",
        "",
        f"- **Persona:** `{p.id}` · {p.caller_name} · caller ID `{p.caller_id or 'none'}`",
        f"- **Shows:** {p.shows}",
        f"- **Result:** {'PASS' if passed == len(r.checks) else 'FAIL'} ({passed}/{len(r.checks)} checks)",
        f"- **Model:** `{a.model}` · effort `{a.effort}` · turn latency p50 {summ['latency_ms']['p50']} ms, "
        f"max {summ['latency_ms']['max']} ms",
        "",
        "## Transcript",
        "",
        "Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.",
        "",
    ]
    for e in r.events:
        if e["event"] == "caller_turn":
            lines += [f"**Caller:** {e['text']}", ""]
        elif e["event"] == "tool_call":
            tag = "[system] " if e["source"] == "system" else ""
            flag = " ⚠️ refused" if e["is_error"] else ""
            lines += [f"> {tag}`{e['tool']}` `{_short(e['input'], 160)}` → `{_short(e['result'])}`{flag}", ""]
        elif e["event"] == "agent_turn":
            lat = f" _({e['latency_ms']} ms)_" if e["latency_ms"] else ""
            lines += [f"**Bookly:** {e['text']}{lat}", ""]
    lines += ["## Checks", "", "| Check | Result |", "|---|---|"]
    for name, ok, note in r.checks:
        lines.append(f"| {name} | {'✅' if ok else '❌ ' + note} |")
    if a.state.handoff:
        lines += ["", "## Handoff packet (what the human agent receives)", "", "```json",
                  json.dumps(a.state.handoff, indent=2), "```"]
    lines += ["", "## End-of-call summary", "", "```json", json.dumps(summ, indent=2, default=str), "```", ""]
    path = out_dir / f"{p.id}.md"
    path.write_text("\n".join(lines))
    return path


def write_index(results: list[SimResult], out_dir: Path) -> None:
    a = results[0].agent
    rows = ["# Simulation results", "",
            f"Model `{a.model}` · effort `{a.effort}` · run {time.strftime('%Y-%m-%d %H:%M')}", "",
            "| Persona | Shows | Checks | p50 / max turn latency | Transcript |", "|---|---|---|---|---|"]
    for r in results:
        passed = sum(ok for _, ok, _ in r.checks)
        lat = r.agent.summary()["latency_ms"]
        status = "✅" if passed == len(r.checks) else "❌"
        rows.append(f"| {r.persona.title} | {r.persona.shows} | {status} {passed}/{len(r.checks)} | "
                    f"{lat['p50']} / {lat['max']} ms | [{r.persona.id}.md]({r.persona.id}.md) |")
    (out_dir / "README.md").write_text("\n".join(rows) + "\n")


# ---------------------------------------------------------------------------
# A/B latency comparison: same personas, configs interleaved, in one run.
# ---------------------------------------------------------------------------
# Opus 5.5 list prices per million tokens (cached in the claude-api skill, not re-checked live).
PRICE = {"input": 4.00, "cache_write": 5.00, "cache_read": 0.20, "output": 20.00}


def parse_config(spec: str) -> tuple[str, dict]:
    name, _, rest = spec.partition(":")
    kw: dict[str, Any] = {}
    for pair in filter(None, rest.split(",")):
        k, _, v = pair.partition("=")
        kw[k] = (v == "1") if k in ("prefetch", "terminal_say") else v
    return name, kw


def _pct(xs: list[int], p: float) -> int | None:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else None


def compare(config_specs: list[str], repeats: int, only: str | None) -> None:
    configs = [parse_config(c) for c in config_specs]
    personas = [p for p in PERSONAS if not only or p.id == only]
    run_dir = db.ROOT / "logs" / "sim" / (time.strftime("%Y%m%d-%H%M%S") + "-compare")
    run_dir.mkdir(parents=True, exist_ok=True)
    jobs = [(p, f"-{name}-{i}", name, kw) for i in range(repeats) for p in personas for name, kw in configs]
    print(f"{len(jobs)} simulated calls ({len(personas)} personas x {len(configs)} configs x {repeats}) "
          f"→ {run_dir.relative_to(db.ROOT)}")
    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(lambda j: (j[2], run_persona(j[0], run_dir, j[1], j[3])), jobs))

    rows = ["| Config | Calls passed | Checks | Turn p50 | Turn p90 | Model calls / turn | Agent cost / call (est.) |",
            "|---|---|---|---|---|---|---|"]
    for name, kw in configs:
        rs = [r for n, r in results if n == name]
        lat, ncalls, nturns, cost = [], 0, 0, 0.0
        for r in rs:
            turn_calls = 0
            for e in r.events:
                if e["event"] == "model_call":
                    turn_calls += 1
                    ncalls += 1
                    cost += (e["input_tokens"] * PRICE["input"] + (e["cache_write"] or 0) * PRICE["cache_write"]
                             + (e["cache_read"] or 0) * PRICE["cache_read"] + e["output_tokens"] * PRICE["output"]) / 1e6
                if e["event"] == "agent_turn" and e["latency_ms"] > 0:
                    lat.append(e["latency_ms"])
                    nturns += 1
        passed_calls = sum(all(ok for _, ok, _ in r.checks) for r in rs)
        checks_ok = sum(ok for r in rs for _, ok, _ in r.checks)
        checks_n = sum(len(r.checks) for r in rs)
        rows.append(f"| `{name}` {kw or ''} | {passed_calls}/{len(rs)} | {checks_ok}/{checks_n} | "
                    f"{_pct(lat, .5)} ms | {_pct(lat, .9)} ms | {ncalls / max(nturns, 1):.2f} | "
                    f"${cost / max(len(rs), 1):.3f} |")
        for r in rs:
            for cname, ok, note in r.checks:
                if not ok:
                    rows.append(f"|  ✗ `{r.persona.id}` | {cname} {note} | | | | | |")
    table = "\n".join(rows)
    (run_dir / "compare.md").write_text(f"# Latency comparison\n\n{len(jobs)} calls, {repeats} repeat(s)\n\n{table}\n")
    print(table)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="Run one persona id")
    ap.add_argument("--no-write", action="store_true", help="Don't overwrite docs/transcripts")
    ap.add_argument("--compare", nargs="+", metavar="NAME:k=v,...",
                    help='A/B configs, e.g. base: fast:prefetch=1,terminal_say=1 med:effort=medium')
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--suite", choices=["core", "edge"], default="core",
                    help="core: the 6 requirement personas; edge: edge-case callers (bookly/edge_cases.py)")
    args = ap.parse_args()
    if args.compare:
        compare(args.compare, args.repeats, args.only)
        return

    if args.suite == "edge":
        from bookly.edge_cases import EDGE_PERSONAS
        pool, transcripts = EDGE_PERSONAS, TRANSCRIPTS / "edge"
    else:
        pool, transcripts = PERSONAS, TRANSCRIPTS
    personas = [p for p in pool if not args.only or p.id == args.only]
    run_dir = db.ROOT / "logs" / "sim" / (time.strftime("%Y%m%d-%H%M%S") + f"-{args.suite}")
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"Running {len(personas)} simulation(s) → logs in {run_dir.relative_to(db.ROOT)}")

    with ThreadPoolExecutor(max_workers=min(len(personas), 8)) as ex:
        results = list(ex.map(lambda p: run_persona(p, run_dir), personas))

    transcripts.mkdir(parents=True, exist_ok=True)
    out_dir = transcripts if not args.no_write else run_dir
    all_ok = True
    for r in results:
        path = write_transcript(r, out_dir)
        passed = sum(ok for _, ok, _ in r.checks)
        ok = passed == len(r.checks)
        all_ok &= ok
        lat = r.agent.summary()["latency_ms"]
        print(f"{'PASS' if ok else 'FAIL'}  {r.persona.id:<24} {passed}/{len(r.checks)}  "
              f"p50 {lat['p50']} ms  → {path.relative_to(db.ROOT)}")
        for name, good, note in r.checks:
            if not good:
                print(f"        ✗ {name} {note}")
    if not args.only:
        write_index(results, out_dir)
    raise SystemExit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
