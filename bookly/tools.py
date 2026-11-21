"""Bookly tools: schemas the model sees + handlers that enforce the rules.

Design rule: the prompt tells the model what to do; these handlers refuse
when the preconditions in CallState aren't met. A tool error comes back to
the model with `guidance` so it can recover in the conversation instead of
guessing.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from bookly.db import ROOT
from bookly.state import CallState, PendingAction

RETURN_WINDOW_DAYS = 30
FAQ_PATH = ROOT / "data" / "faq.md"

TRANSFER_REASONS = [
    "angry_or_repeat_caller",
    "lost_or_damaged",
    "outside_policy",
    "unclear_intent",
    "faq_not_found",
    "verification_failed",
    "caller_requested",
    "other",
]


class ToolError(Exception):
    def __init__(self, code: str, message: str, guidance: str = ""):
        super().__init__(message)
        self.code, self.message, self.guidance = code, message, guidance

    def to_dict(self) -> dict[str, Any]:
        return {"error": self.code, "message": self.message, "guidance": self.guidance}


@dataclass
class ToolContext:
    conn: sqlite3.Connection
    state: CallState


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _money(cents: int) -> str:
    return f"${cents / 100:.2f}"


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def spoken_date(iso: str | None) -> str | None:
    """'2026-11-23' -> 'Monday, November 23rd' (year added only if not this year).
    Tools hand the model the words to say, so it never works out a weekday itself."""
    if not iso:
        return None
    d = date.fromisoformat(iso)
    n = d.day
    suffix = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    out = f"{d.strftime('%A, %B')} {n}{suffix}"
    return out if d.year == date.today().year else f"{out}, {d.year}"


def _mask_email(email: str) -> str:
    user, _, domain = email.partition("@")
    return f"{user[0]}***@{domain}"


# --------------------------------------------------------------------------
# Data helpers
# --------------------------------------------------------------------------
def _customer_row(conn, **where) -> dict | None:
    (col, val), = where.items()
    r = conn.execute(f"SELECT * FROM customers WHERE {col} = ?", (val,)).fetchone()
    return dict(r) if r else None


def order_summaries(conn, customer_id: int) -> list[dict[str, Any]]:
    orders = conn.execute(
        "SELECT order_number, placed_at FROM orders WHERE customer_id = ? ORDER BY placed_at DESC",
        (customer_id,),
    ).fetchall()
    out = []
    for o in orders:
        items = conn.execute(
            "SELECT title, author FROM order_items WHERE order_number = ?", (o["order_number"],)
        ).fetchall()
        out.append({"order_number": o["order_number"], "placed_at": spoken_date(o["placed_at"]),
                    "items": [dict(i) for i in items]})
    return out


def _require_identified(state: CallState) -> dict:
    if not state.identified or not state.verified_customer:
        raise ToolError(
            "not_identified",
            "The caller hasn't been identified yet.",
            "Ask for their order number (or, as a last resort, the email on their account).",
        )
    return state.verified_customer


def _require_zip(state: CallState) -> None:
    if state.zip_locked:
        raise ToolError(
            "verification_locked",
            "ZIP verification failed twice, so no changes can be made on this call.",
            "Apologise and offer to transfer to a specialist (reason verification_failed).",
        )
    if not state.zip_verified:
        raise ToolError(
            "zip_required",
            "Changes need the ZIP code on the account to be verified first.",
            "Explain why you need it, ask for the ZIP code, and call verify_zip.",
        )


def _load_order(ctx: ToolContext, order_number: str) -> sqlite3.Row:
    num = _digits(order_number)
    row = ctx.conn.execute("SELECT * FROM orders WHERE order_number = ?", (num,)).fetchone()
    st = ctx.state
    not_found = ToolError(
        "order_not_found",
        f"No order {num or order_number!r} found" + (" on this account." if st.identified else "."),
        "Read the number back digit by digit and ask the caller to check it. Don't guess.",
    )
    if not row:
        raise not_found
    if st.identified:
        if row["customer_id"] != st.verified_customer["id"]:
            raise not_found  # never reveal another customer's order exists
        if st.scoped_order and st.scoped_order != num:
            raise ToolError(
                "out_of_scope",
                "This caller was identified by a single order number, so only that order is accessible.",
                "Ask for the email on the account if they need help with another order.",
            )
    return row


def _item_eligibility(order: sqlite3.Row, item_id: int, existing: dict | None) -> tuple[bool, str | None, str | None]:
    """returns (returnable, reason_if_not, window_ends)"""
    if existing:
        return False, f"already_returned ({existing['resolution']}, {existing['status']})", None
    status = order["status"]
    if status == "processing":
        return False, "not_shipped_yet: offer to cancel the order instead", None
    if status == "shipped":
        return False, "not_delivered_yet: can be returned after delivery", None
    if status == "lost":
        return False, "lost_in_transit: transfer to a specialist", None
    if status == "cancelled":
        return False, "order_cancelled", None
    delivered = date.fromisoformat(order["delivered_at"])
    days = (date.today() - delivered).days
    window_ends = date.fromordinal(delivered.toordinal() + RETURN_WINDOW_DAYS).isoformat()
    if days > RETURN_WINDOW_DAYS:
        return False, (f"outside_30_day_window: delivered {spoken_date(order['delivered_at'])} ({days} days ago), "
                       f"window ended {spoken_date(window_ends)}"), window_ends
    return True, None, window_ends


def _order_view(ctx: ToolContext, order: sqlite3.Row) -> dict[str, Any]:
    items = ctx.conn.execute(
        "SELECT * FROM order_items WHERE order_number = ? ORDER BY id", (order["order_number"],)
    ).fetchall()
    out_items = []
    for it in items:
        ret = ctx.conn.execute("SELECT * FROM returns WHERE item_id = ?", (it["id"],)).fetchone()
        ret = dict(ret) if ret else None
        ok, why, window_ends = _item_eligibility(order, it["id"], ret)
        out_items.append({
            "item_id": it["id"], "title": it["title"], "author": it["author"],
            "format": it["format"], "price": _money(it["price_cents"]),
            "returnable": ok, "not_returnable_reason": why, "return_window_ends": spoken_date(window_ends),
            "existing_return": ({"return_id": ret["id"], "resolution": ret["resolution"], "status": ret["status"]}
                                if ret else None),
        })
    view = {
        "order_number": order["order_number"],
        "status": order["status"],
        "placed_at": spoken_date(order["placed_at"]),
        "shipped_at": spoken_date(order["shipped_at"]),
        "delivered_at": spoken_date(order["delivered_at"]),
        "estimated_delivery": spoken_date(order["eta"]) if order["status"] in ("processing", "shipped") else None,
        "carrier": order["carrier"],
        "has_tracking": bool(order["tracking_number"]),
        "cancellable": order["status"] == "processing",
        "items": out_items,
    }
    if order["status"] == "lost":
        view["note"] = "Carrier has marked this order lost. Escalate: transfer_to_human with reason lost_or_damaged."
    return view


# --------------------------------------------------------------------------
# Two-phase confirmation for writes
# --------------------------------------------------------------------------
def _two_phase(ctx: ToolContext, action: str, key: str, read_back: str, confirmed: bool,
               execute: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    st = ctx.state
    if not confirmed:
        st.pending_action = PendingAction(action=action, key=key, read_back=read_back,
                                          proposed_at_turn=st.caller_turns)
        return {
            "status": "needs_confirmation",
            "read_back": read_back,
            "instruction": "Read this back to the caller and ask for a clear yes. "
                           "Only after they agree, call this tool again with the same arguments and confirmed=true.",
        }
    pa = st.pending_action
    if not pa or pa.action != action or pa.key != key:
        raise ToolError(
            "not_read_back",
            "This change hasn't been read back to the caller yet (or the details changed).",
            "Call the tool without confirmed to get the read-back, say it, and wait for a yes.",
        )
    if st.caller_turns <= pa.proposed_at_turn:
        raise ToolError(
            "awaiting_caller",
            "The caller hasn't answered the read-back yet.",
            "Say the read-back and wait for the caller's reply before confirming.",
        )
    result = execute()
    st.pending_action = None
    return result


# --------------------------------------------------------------------------
# Tool handlers
# --------------------------------------------------------------------------
def lookup_customer(ctx: ToolContext, method: str, email: str | None = None) -> dict[str, Any]:
    st = ctx.state
    if method == "caller_id":
        if not st.caller_id:
            raise ToolError("no_caller_id", "No caller ID on this call.",
                            "Ask for their order number.")
        cust = _customer_row(ctx.conn, phone=st.caller_id)
        if not cust:
            return {"found": False, "message": "Caller ID doesn't match any account.",
                    "guidance": "Ask for their order number; use email only as a last resort."}
    elif method == "email":
        if not email:
            raise ToolError("missing_email", "No email given.", "Ask the caller for the email on their account.")
        cust = _customer_row(ctx.conn, email=email.strip().lower())
        if not cust:
            return {"found": False, "message": "No account with that email.",
                    "guidance": "Spell the email back to check it. If it still doesn't match, offer a transfer."}
    else:
        raise ToolError("bad_method", f"Unknown method {method!r}.", "Use caller_id or email.")

    if st.verified_customer and st.verified_customer["id"] != cust["id"]:
        raise ToolError("already_identified", "This call is already linked to a different account.",
                        "Don't switch accounts mid-call. Offer a transfer if needed.")
    st.identify(cust, via=method)
    st.scoped_order = None  # caller ID / email gives account-level read access
    orders = order_summaries(ctx.conn, cust["id"])
    return {
        "found": True,
        "customer": {"name": cust["name"], "repeat_caller": cust["recent_contacts"] >= 2,
                     "recent_contacts": cust["recent_contacts"]},
        "orders": orders,
        "note": "Statuses aren't included. Confirm which order the caller means, then call lookup_order.",
    }


def lookup_order(ctx: ToolContext, order_number: str) -> dict[str, Any]:
    st = ctx.state
    row = _load_order(ctx, order_number)
    if not st.identified:
        cust = _customer_row(ctx.conn, id=row["customer_id"])
        st.identify(cust, via="order_number", scoped_order=row["order_number"])
    st.selected_order = row["order_number"]
    return {"customer_name": st.verified_customer["name"], "order": _order_view(ctx, row)}


def verify_zip(ctx: ToolContext, zip: str) -> dict[str, Any]:
    st = ctx.state
    cust = _require_identified(st)
    if st.zip_verified:
        return {"verified": True, "message": "ZIP already verified on this call."}
    if st.zip_locked:
        _require_zip(st)
    z = _digits(zip)[:5]
    valid = {cust["zip"]}
    if st.selected_order:
        r = ctx.conn.execute("SELECT ship_zip FROM orders WHERE order_number = ?", (st.selected_order,)).fetchone()
        if r:
            valid.add(r["ship_zip"])
    if len(z) == 5 and z in valid:
        st.verification_level = "zip_verified"
        return {"verified": True}
    st.zip_failures += 1
    left = max(0, 2 - st.zip_failures)
    return {
        "verified": False,
        "attempts_left": left,
        "guidance": ("Read back what you heard digit by digit and ask once more."
                     if left else "No attempts left. No changes allowed; offer a transfer (verification_failed)."),
    }


def cancel_order(ctx: ToolContext, order_number: str, confirmed: bool = False) -> dict[str, Any]:
    st = ctx.state
    _require_identified(st)
    order = _load_order(ctx, order_number)
    st.selected_order = order["order_number"]
    if order["status"] == "cancelled":
        return {"status": "already_cancelled", "idempotent": True}
    if order["status"] != "processing":
        raise ToolError("not_cancellable",
                        f"Order is {order['status']}; only processing orders can be cancelled.",
                        "Explain this. Shipped orders can be returned after delivery.")
    _require_zip(st)
    titles = ", ".join(
        f"{r['title']} by {r['author']}" for r in
        ctx.conn.execute("SELECT title, author FROM order_items WHERE order_number = ?", (order["order_number"],))
    )
    total = ctx.conn.execute("SELECT SUM(price_cents) s FROM order_items WHERE order_number = ?",
                             (order["order_number"],)).fetchone()["s"]
    read_back = (f"Cancel order {order['order_number']} ({titles}). "
                 f"The {_money(total)} charge will be released to the original payment method.")

    def execute():
        ctx.conn.execute("UPDATE orders SET status = 'cancelled' WHERE order_number = ? AND status = 'processing'",
                         (order["order_number"],))
        ctx.conn.commit()
        st.actions_taken.append(f"cancelled order {order['order_number']}")
        return {"status": "cancelled", "order_number": order["order_number"],
                "next_steps": f"The {_money(total)} authorisation is released within 3 to 5 business days."}

    return _two_phase(ctx, "cancel_order", f"cancel:{order['order_number']}", read_back, confirmed, execute)


def start_return(ctx: ToolContext, order_number: str, item_id: int, reason: str, resolution: str,
                 confirmed: bool = False) -> dict[str, Any]:
    st = ctx.state
    _require_identified(st)
    order = _load_order(ctx, order_number)
    st.selected_order = order["order_number"]
    item = ctx.conn.execute("SELECT * FROM order_items WHERE id = ? AND order_number = ?",
                            (item_id, order["order_number"])).fetchone()
    if not item:
        raise ToolError("item_not_in_order", "That book isn't in this order.",
                        "Confirm the title and author with the caller, using item_id from lookup_order.")
    existing = ctx.conn.execute("SELECT * FROM returns WHERE item_id = ?", (item_id,)).fetchone()
    if existing:  # idempotent: the same return twice is a no-op that reports the original
        return {"status": "already_exists", "idempotent": True, "return_id": existing["id"],
                "resolution": existing["resolution"], "return_status": existing["status"]}
    ok, why, _ = _item_eligibility(order, item_id, None)
    if not ok:
        if why.startswith("outside_30_day_window"):
            raise ToolError("outside_policy", f"Not returnable: {why}.",
                            "State the 30-day policy plainly. Don't offer or hint at exceptions. "
                            "Offer a transfer (reason outside_policy).")
        raise ToolError("not_returnable", f"Not returnable: {why}.", "Explain simply; follow the procedure.")
    if resolution not in ("refund", "store_credit"):
        raise ToolError("bad_resolution", "Resolution must be refund or store_credit.", "")
    if not (reason or "").strip():
        raise ToolError("missing_reason", "A return reason is required.", "Ask why they're returning it.")
    _require_zip(st)

    amount = item["price_cents"]
    book = f"{item['title']} by {item['author']}"
    if resolution == "refund":
        outcome = f"refunded {_money(amount)} to the original payment method once we receive the book"
    else:
        outcome = f"{_money(amount)} in store credit added to the account right away"
    read_back = f"Return {book} from order {order['order_number']}, {outcome}."

    def execute():
        status = "awaiting_book"
        cur = ctx.conn.execute(
            "INSERT INTO returns (order_number,item_id,reason,resolution,amount_cents,status,created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (order["order_number"], item_id, reason.strip(), resolution, amount, status, _now()),
        )
        ctx.conn.commit()
        rid = cur.lastrowid
        st.actions_taken.append(f"return #{rid}: {book} ({resolution}, {_money(amount)})")
        res = {"status": "return_started", "return_id": rid, "resolution": resolution,
               "amount": _money(amount),
               "next_steps": "A prepaid return label is emailed to the address on file. "
                             + ("Refund issues 5 to 7 business days after we receive the book."
                                if resolution == "refund" else
                                "Call issue_store_credit with this return_id to add the credit now.")}
        return res

    key = f"return:{order['order_number']}:{item_id}:{resolution}"
    return _two_phase(ctx, "start_return", key, read_back, confirmed, execute)


def issue_store_credit(ctx: ToolContext, return_id: int) -> dict[str, Any]:
    st = ctx.state
    cust = _require_identified(st)
    _require_zip(st)
    ret = ctx.conn.execute(
        "SELECT r.*, o.customer_id FROM returns r JOIN orders o ON o.order_number = r.order_number WHERE r.id = ?",
        (return_id,),
    ).fetchone()
    if not ret or ret["customer_id"] != cust["id"]:
        raise ToolError("return_not_found", "No such return on this account.", "Use the return_id from start_return.")
    if ret["resolution"] != "store_credit":
        raise ToolError("not_store_credit", "This return was set up as a refund, not store credit.",
                        "Don't issue credit for a refund return.")
    if ret["credit_issued"]:
        return {"status": "already_issued", "idempotent": True, "amount": _money(ret["amount_cents"])}
    ctx.conn.execute("UPDATE returns SET credit_issued = 1, status = 'credit_issued' WHERE id = ?", (return_id,))
    ctx.conn.execute("UPDATE customers SET store_credit_cents = store_credit_cents + ? WHERE id = ?",
                     (ret["amount_cents"], cust["id"]))
    ctx.conn.commit()
    bal = ctx.conn.execute("SELECT store_credit_cents FROM customers WHERE id = ?", (cust["id"],)).fetchone()[0]
    st.actions_taken.append(f"store credit {_money(ret['amount_cents'])} for return #{return_id}")
    return {"status": "credit_issued", "amount": _money(ret["amount_cents"]), "new_balance": _money(bal)}


def search_faq(ctx: ToolContext, query: str) -> dict[str, Any]:
    hits = faq_search(query)
    if not hits:
        return {"found": False,
                "guidance": "The FAQ doesn't cover this. Say you don't have that answer and offer a transfer. "
                            "Don't answer from general knowledge."}
    return {"found": True, "results": hits,
            "guidance": "Answer only from these results, in one or two spoken sentences."}


def send_password_reset(ctx: ToolContext, confirmed: bool = False) -> dict[str, Any]:
    st = ctx.state
    cust = _require_identified(st)
    _require_zip(st)
    masked = _mask_email(cust["email"])
    read_back = f"Email a password reset link to the address on file ({masked})."

    def execute():
        _outbox(ctx, "email", cust["email"], "password_reset",
                "Reset your Bookly password: https://bookly.example/reset/<token> (expires in 30 minutes)",
                dedupe=f"{st.call_id}:password_reset")
        st.actions_taken.append("password reset email sent")
        return {"status": "sent", "to": masked, "expires_in_minutes": 30}

    return _two_phase(ctx, "send_password_reset", f"pwreset:{cust['id']}", read_back, confirmed, execute)


def send_confirmation(ctx: ToolContext, kind: str, channel: str, order_number: str | None = None) -> dict[str, Any]:
    """Receipt or tracking by SMS/email. Mocked: written to the outbox table + tool log
    (A2P 10DLC isn't registered, so no real SMS). Only to the caller ID or email on file."""
    st = ctx.state
    cust = _require_identified(st)
    if channel == "sms":
        if not st.caller_id:
            raise ToolError("no_caller_id", "No number to text on this call.", "Offer email instead.")
        to = st.caller_id
    elif channel == "email":
        to = cust["email"]
    else:
        raise ToolError("bad_channel", "Channel must be sms or email.", "")

    if order_number:
        st.selected_order = _load_order(ctx, order_number)["order_number"]
    if kind == "tracking":
        if not st.selected_order:
            raise ToolError("no_order", "No order selected.", "Confirm which order first.")
        o = ctx.conn.execute("SELECT * FROM orders WHERE order_number = ?", (st.selected_order,)).fetchone()
        if not o["tracking_number"]:
            raise ToolError("no_tracking", "This order has no tracking number yet.", "Say so; don't invent one.")
        body = f"Bookly order {o['order_number']}: {o['carrier']} tracking {o['tracking_number']}"
        ref = o["order_number"]
    elif kind == "receipt":
        if not st.actions_taken:
            raise ToolError("nothing_to_confirm", "No completed change on this call to send a receipt for.",
                            "Only offer a receipt after a change is made.")
        body = "Bookly receipt: " + "; ".join(st.actions_taken)
        ref = str(len(st.actions_taken))
    else:
        raise ToolError("bad_kind", "Kind must be receipt or tracking.", "")

    sent = _outbox(ctx, channel, to, kind, body, dedupe=f"{st.call_id}:{kind}:{ref}:{channel}")
    shown = to if channel == "email" else f"***-***-{to[-4:]}"
    return {"status": "sent" if sent else "already_sent", "channel": channel, "to": shown,
            "mock": True, "note": "Delivery is mocked (written to the outbox)."}


def transfer_to_human(ctx: ToolContext, reason: str, summary: str, caller_wants: str,
                      order_number: str | None = None, say_to_caller: str | None = None) -> dict[str, Any]:
    st = ctx.state
    if order_number:
        try:
            st.selected_order = _load_order(ctx, order_number)["order_number"]
        except ToolError:
            pass  # never block a handoff on a bad order number
    c = st.verified_customer
    packet = {
        "reason": reason,
        "caller_wants": caller_wants,
        "summary": summary,
        "customer": ({"id": c["id"], "name": c["name"], "phone_on_file": c["phone"], "email": c["email"]}
                     if c else None),
        "caller_id": st.caller_id,
        "identified_via": st.identified_via,
        "zip_verified": st.zip_verified,
        "selected_order": st.selected_order,
        "actions_taken": list(st.actions_taken),
        "pending_unconfirmed_change": st.pending_action.read_back if st.pending_action else None,
    }
    st.handoff = packet
    st.ended = True
    st.end_reason = f"transfer:{reason}"
    st.closing_line = (say_to_caller or "").strip() or None
    return {"status": "transferring",
            "instruction": "Tell the caller in one sentence that you're connecting them with a specialist "
                           "who will have these details, so they won't need to repeat themselves. Then stop."}


def end_call(ctx: ToolContext, reason: str, goodbye: str | None = None) -> dict[str, Any]:
    ctx.state.ended = True
    ctx.state.end_reason = f"end:{reason}"
    ctx.state.closing_line = (goodbye or "").strip() or None
    return {"status": "ending", "instruction": "Say a one-sentence goodbye."}


def _outbox(ctx: ToolContext, channel: str, to: str, kind: str, body: str, dedupe: str) -> bool:
    try:
        ctx.conn.execute(
            "INSERT INTO outbox (channel,recipient,kind,body,dedupe_key,created_at) VALUES (?,?,?,?,?,?)",
            (channel, to, kind, body, dedupe, _now()),
        )
        ctx.conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


# --------------------------------------------------------------------------
# FAQ search: keyword scoring over ## sections. No vector DB: the FAQ is
# small, and exact, auditable matches beat fuzzy recall for policy answers.
# --------------------------------------------------------------------------
_STOP = set("""a an the and or but if to of for in on at by with from is are was were be been do does did
can could would should will i me my you your we our it its this that what when where how why which who
about any there their them they get got have has had not no yes please just so as than then too very
much many some one""".split())


def _stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > 4 and w.endswith(suf):
            w = w[: -len(suf)]
            if len(w) > 2 and w[-1] == w[-2]:  # shipping -> shipp -> ship
                w = w[:-1]
            return w
    return w


def _tokens(text: str) -> set[str]:
    return {_stem(w) for w in re.findall(r"[a-z]+", text.lower()) if w not in _STOP}


def _faq_sections(path: Path = FAQ_PATH) -> list[tuple[str, str]]:
    text = path.read_text()
    parts = re.split(r"^## +(.+)$", text, flags=re.M)
    return [(parts[i].strip(), parts[i + 1].strip()) for i in range(1, len(parts), 2)]


def faq_search(query: str, limit: int = 2) -> list[dict[str, str]]:
    q = _tokens(query)
    scored = []
    for heading, body in _faq_sections():
        h, b = _tokens(heading), _tokens(body)
        score = 3 * len(q & h) + len(q & b)
        if q & h or len(q & b) >= 2:
            scored.append((score, heading, body))
    scored.sort(reverse=True)
    return [{"topic": h, "answer": b} for _, h, b in scored[:limit]]


# --------------------------------------------------------------------------
# Schemas (what the model sees). Order is fixed so the prompt cache holds.
# --------------------------------------------------------------------------
def _schema(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


CONFIRMED = {"type": "boolean",
             "description": "Leave false/omit to get the read-back. Set true only after the caller said yes to it."}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "lookup_customer",
        "description": "Find the caller's account. 'caller_id' uses the carrier caller ID (never a number the "
                       "caller speaks). 'email' is the last resort, after order number. Returns orders by book "
                       "(no statuses) so you can ask which one they mean.",
        "input_schema": _schema({
            "method": {"type": "string", "enum": ["caller_id", "email"]},
            "email": {"type": "string", "description": "Only for method=email."},
        }, ["method"]),
    },
    {
        "name": "lookup_order",
        "description": "Get live status, dates, carrier and books (with return eligibility) for one order. "
                       "Also identifies a caller with no caller-ID match (read access to that order only).",
        "input_schema": _schema({
            "order_number": {"type": "string", "description": "6-digit order number."},
        }, ["order_number"]),
    },
    {
        "name": "verify_zip",
        "description": "Verify the ZIP code on file. Required before any change. Two failures lock changes.",
        "input_schema": _schema({"zip": {"type": "string"}}, ["zip"]),
    },
    {
        "name": "cancel_order",
        "description": "Cancel an order that is still processing. Two-phase: first call returns a read-back; "
                       "call again with confirmed=true after the caller agrees. Needs ZIP verification.",
        "input_schema": _schema({"order_number": {"type": "string"}, "confirmed": CONFIRMED}, ["order_number"]),
    },
    {
        "name": "start_return",
        "description": "Start a return for one book within the 30-day window, as a refund (after the book is "
                       "received) or store credit (immediate). Two-phase like cancel_order. Needs ZIP verification. "
                       "Idempotent per book.",
        "input_schema": _schema({
            "order_number": {"type": "string"},
            "item_id": {"type": "integer", "description": "item_id from lookup_order."},
            "reason": {"type": "string", "description": "The caller's reason, in a few words."},
            "resolution": {"type": "string", "enum": ["refund", "store_credit"]},
            "confirmed": CONFIRMED,
        }, ["order_number", "item_id", "reason", "resolution"]),
    },
    {
        "name": "issue_store_credit",
        "description": "Add store credit for a confirmed store-credit return. Idempotent per return.",
        "input_schema": _schema({"return_id": {"type": "integer"}}, ["return_id"]),
    },
    {
        "name": "search_faq",
        "description": "Search Bookly's FAQ (shipping, policies, accounts, payment). Answer general questions "
                       "only from its results.",
        "input_schema": _schema({"query": {"type": "string"}}, ["query"]),
    },
    {
        "name": "send_password_reset",
        "description": "Email a password reset link to the address on file (mocked). Needs ZIP verification. "
                       "Two-phase.",
        "input_schema": _schema({"confirmed": CONFIRMED}, []),
    },
    {
        "name": "send_confirmation",
        "description": "Send a receipt (after a change) or tracking number by SMS to the caller's number or email "
                       "on file. Only when the caller asked or agreed. Mocked delivery.",
        "input_schema": _schema({
            "kind": {"type": "string", "enum": ["receipt", "tracking"]},
            "channel": {"type": "string", "enum": ["sms", "email"]},
        }, ["kind", "channel"]),
    },
    {
        "name": "transfer_to_human",
        "description": "Hand the call to a person with a structured summary so the caller never repeats "
                       "themselves. Use for angry/repeat callers, lost or damaged orders, out-of-policy requests, "
                       "unclear intent after one clarifying question, FAQ gaps, failed verification, or on request.",
        "input_schema": _schema({
            "reason": {"type": "string", "enum": TRANSFER_REASONS},
            "caller_wants": {"type": "string", "description": "What the caller wants, in one sentence."},
            "summary": {"type": "string",
                        "description": "What you checked and found (order, book, status, policy), and what's unresolved."},
        }, ["reason", "caller_wants", "summary"]),
    },
    {
        "name": "end_call",
        "description": "End the call after the caller is done and you've said goodbye.",
        "input_schema": _schema({"reason": {"type": "string", "enum": ["resolved", "caller_left", "no_response"]}},
                                ["reason"]),
    },
]


def tool_schemas(prefetch: bool = False, terminal_say: bool = False) -> list[dict[str, Any]]:
    """Variants for latency experiments; the default is TOOL_SCHEMAS unchanged.

    prefetch:     order details are already in the call-state note, so tools that act on an order
                  take order_number directly instead of relying on a prior lookup_order.
    terminal_say: end_call / transfer_to_human carry the line to speak, so the call ends without
                  another model round trip after the tool runs.
    """
    import copy
    out = copy.deepcopy(TOOL_SCHEMAS)
    by = {t["name"]: t for t in out}
    order_prop = {"type": "string", "description": "6-digit order number this is about, if any."}
    if prefetch:
        by["send_confirmation"]["input_schema"]["properties"]["order_number"] = order_prop
        by["transfer_to_human"]["input_schema"]["properties"]["order_number"] = order_prop
    if terminal_say:
        t = by["transfer_to_human"]
        t["description"] += (" The call ends when this runs: put the one sentence you'll say to the caller in "
                             "say_to_caller (e.g. that you're connecting them with a specialist who will have the "
                             "details), and don't write it anywhere else.")
        t["input_schema"]["properties"]["say_to_caller"] = {"type": "string"}
        t["input_schema"]["required"].append("say_to_caller")
        e = by["end_call"]
        e["description"] = ("End the call when the caller is done. Put your one-sentence goodbye in `goodbye`; "
                            "it is spoken and the call ends, so don't write it anywhere else.")
        e["input_schema"]["properties"]["goodbye"] = {"type": "string"}
        e["input_schema"]["required"].append("goodbye")
    return out


HANDLERS: dict[str, Callable[..., dict[str, Any]]] = {
    "lookup_customer": lookup_customer,
    "lookup_order": lookup_order,
    "verify_zip": verify_zip,
    "cancel_order": cancel_order,
    "start_return": start_return,
    "issue_store_credit": issue_store_credit,
    "search_faq": search_faq,
    "send_password_reset": send_password_reset,
    "send_confirmation": send_confirmation,
    "transfer_to_human": transfer_to_human,
    "end_call": end_call,
}

WRITE_TOOLS = {"cancel_order", "start_return", "issue_store_credit", "send_password_reset"}


def run_tool(ctx: ToolContext, name: str, args: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Returns (result, is_error)."""
    fn = HANDLERS.get(name)
    if not fn:
        return {"error": "unknown_tool", "message": name}, True
    try:
        return fn(ctx, **args), False
    except ToolError as e:
        return e.to_dict(), True
    except TypeError as e:  # bad/missing args
        return {"error": "bad_arguments", "message": str(e)}, True
