"""Per-call JSONL log: every transcript turn, tool call and per-turn latency.

One file per call in logs/. Never log environment variables or keys.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bookly.db import ROOT

LOG_DIR = ROOT / "logs"


class CallLogger:
    def __init__(self, call_id: str, log_dir: Path | None = None, echo: bool = False):
        self.call_id = call_id
        self.dir = Path(log_dir or LOG_DIR)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / f"{call_id}.jsonl"
        self.echo = echo
        self.events: list[dict[str, Any]] = []
        self.started = time.monotonic()

    def event(self, kind: str, **data: Any) -> dict[str, Any]:
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "t_ms": round((time.monotonic() - self.started) * 1000),
            "call_id": self.call_id,
            "event": kind,
            **data,
        }
        self.events.append(rec)
        with self.path.open("a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        if self.echo:
            print(f"  · {kind}: {json.dumps(data, default=str)[:240]}")
        return rec

    # convenience views -----------------------------------------------------
    def tool_calls(self) -> list[dict[str, Any]]:
        return [e for e in self.events if e["event"] == "tool_call"]

    def turn_latencies(self) -> list[int]:
        return [e["latency_ms"] for e in self.events if e["event"] == "agent_turn"]
