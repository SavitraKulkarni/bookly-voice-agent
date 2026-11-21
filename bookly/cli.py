"""Text mode: talk to the same agent that runs on the phone.

    python -m bookly.cli --phone +14155550101   # simulate caller ID (Maya Chen)
    python -m bookly.cli                         # no caller ID
    python -m bookly.cli --phone +14155550101 -v # also show tool calls
"""
from __future__ import annotations

import argparse
import json

from bookly.agent import Agent

DIM, BOLD, RESET = "\033[2m", "\033[1m", "\033[0m"


def main() -> None:
    ap = argparse.ArgumentParser(description="Bookly support agent, text mode")
    ap.add_argument("--phone", help="Simulated caller ID in E.164, e.g. +14155550101")
    ap.add_argument("-v", "--verbose", action="store_true", help="Show tool calls and latency")
    args = ap.parse_args()

    agent = Agent(caller_id=args.phone)
    shown = 0

    def show_tools():
        nonlocal shown
        if not args.verbose:
            return
        calls = agent.log.tool_calls()
        for c in calls[shown:]:
            res = json.dumps(c["result"])
            print(f"{DIM}  [{c['source']}] {c['tool']}({json.dumps(c['input'])}) -> "
                  f"{res[:200]}{'…' if len(res) > 200 else ''}  ({c['ms']} ms){RESET}")
        shown = len(calls)

    print(f"{DIM}call {agent.call_id} · caller ID {args.phone or 'none'} · log {agent.log.path}{RESET}")
    show_tools()
    print(f"{BOLD}Bookly:{RESET} {agent.greeting()}")
    try:
        while True:
            text = input(f"{BOLD}You:{RESET} ").strip()
            if not text:
                continue
            reply = agent.handle_turn(text)
            show_tools()
            lat = f"  {DIM}({reply.latency_ms} ms){RESET}" if args.verbose else ""
            print(f"{BOLD}Bookly:{RESET} {reply.text}{lat}")
            if reply.ended:
                if reply.handoff:
                    print(f"\n{DIM}--- handoff to human ---\n{json.dumps(reply.handoff, indent=2)}{RESET}")
                break
    except (KeyboardInterrupt, EOFError):
        print()
    summary = agent.end()
    print(f"{DIM}--- call summary ---\n{json.dumps(summary, indent=2)}{RESET}")


if __name__ == "__main__":
    main()
