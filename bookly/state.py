"""Structured call state, kept separate from the transcript.

The model never edits this directly: only tools change it, and tools check it
before doing anything risky. The prompt explains the rules; this object is
what makes the code refuse when the rules aren't met.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

# How sure we are of who's calling. Writes need "zip_verified".
VERIFICATION_LEVELS = ("none", "identified", "zip_verified")
MAX_ZIP_FAILURES = 2


@dataclass
class PendingAction:
    action: str            # cancel_order | start_return | send_password_reset
    key: str               # identity of the exact change, e.g. "return:418027:1:refund"
    read_back: str
    proposed_at_turn: int  # caller turn count when the read-back was produced
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class CallState:
    call_id: str
    caller_id: str | None = None             # from the carrier, never from speech

    verified_customer: dict[str, Any] | None = None
    verification_level: str = "none"         # none | identified | zip_verified
    identified_via: str | None = None        # caller_id | order_number | email
    scoped_order: str | None = None          # identified by order number -> only this order
    zip_failures: int = 0

    selected_order: str | None = None
    pending_action: PendingAction | None = None

    caller_turns: int = 0
    actions_taken: list[str] = field(default_factory=list)
    ended: bool = False
    end_reason: str | None = None
    handoff: dict[str, Any] | None = None
    closing_line: str | None = None          # spoken line carried by a terminal tool (end_call / transfer)

    # ---- helpers used by tools -------------------------------------------
    @property
    def identified(self) -> bool:
        return self.verification_level in ("identified", "zip_verified")

    @property
    def zip_verified(self) -> bool:
        return self.verification_level == "zip_verified"

    @property
    def zip_locked(self) -> bool:
        return self.zip_failures >= MAX_ZIP_FAILURES

    def identify(self, customer: dict[str, Any], via: str, scoped_order: str | None = None) -> None:
        self.verified_customer = customer
        self.identified_via = via
        self.scoped_order = scoped_order
        if self.verification_level == "none":
            self.verification_level = "identified"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    # ---- what the model sees each turn -----------------------------------
    def snapshot(self, order_summaries: list[dict[str, Any]] | None = None) -> str:
        """Short call-state note injected as an operator (system) message each turn."""
        lines = [f"[Call state] Today is {date.today().strftime('%A, %B %d, %Y')}."]
        if not self.caller_id:
            lines.append("Caller ID: unavailable.")
        elif self.verified_customer and self.identified_via == "caller_id":
            lines.append("Caller ID: matched an account.")
        else:
            lines.append("Caller ID: no matching account.")

        c = self.verified_customer
        if c:
            lines.append(
                f"Customer: {c['name']} (identified via {self.identified_via}; "
                f"ZIP verified: {'yes' if self.zip_verified else 'no'})."
            )
            if c.get("recent_contacts", 0) >= 2:
                lines.append(
                    f"REPEAT CALLER: {c['recent_contacts']} support contacts in the last 14 days. "
                    "Per policy, transfer to a person."
                )
        else:
            lines.append("Customer: not identified yet.")

        if self.scoped_order:
            lines.append(f"Access limited to order {self.scoped_order} (identified by order number).")
        if order_summaries:
            lines.append("Orders on file (for telling them apart only; call lookup_order for live status):")
            for o in order_summaries:
                books = "; ".join(f"{i['title']} by {i['author']}" for i in o["items"])
                lines.append(f"  - order {o['order_number']}, placed {o['placed_at']}: {books}")
        if self.selected_order:
            lines.append(f"Selected order: {self.selected_order}.")
        if self.zip_locked:
            lines.append("ZIP verification failed twice: no changes allowed. Offer a transfer.")
        if self.pending_action:
            lines.append(
                f"Pending change awaiting the caller's yes: {self.pending_action.read_back}"
            )
        return "\n".join(lines)
