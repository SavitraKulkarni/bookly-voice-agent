# Angry repeat caller with a lost order: immediate handoff

- **Persona:** `angry_transfer` · Robert Kim · caller ID `+16175550188`
- **Shows:** knowing when not to decide: escalation with a structured summary, no attempted fixes
- **Result:** PASS (9/9 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 3381 ms, max 3381 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "Robert Kim", "repeat_caller": true, "recent_contacts": 2}, "orders": [{"order_number": "415930", "placed_at": "2026-10-28", "items": [{"title": "The Covenant of Water", "author": "Ab…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** This is the third time I'm calling. My book never showed up and nobody has fixed it!

> `transfer_to_human` `{"reason": "angry_or_repeat_caller", "caller_wants": "Caller wants resolution for a book that never arrived; this is their third call.", "order_number": "415930…` → `{"status": "transferring", "instruction": "Tell the caller in one sentence that you're connecting them with a specialist who will have these details, so they won't need to repeat themselves. Then stop."}`

**Bookly:** I'm so sorry this still isn't fixed, Robert; I'm connecting you with a specialist now and passing along everything about your lost order so you won't have to repeat yourself. _(3381 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words, no markdown/URLs | ✅ |
| transferred | ✅ |
| reason is angry/repeat or lost | ✅ |
| handed off within 2 replies | ✅ |
| no writes attempted | ✅ |
| handoff summary identifies the order/book | ✅ |

## Handoff packet (what the human agent receives)

```json
{
  "reason": "angry_or_repeat_caller",
  "caller_wants": "Caller wants resolution for a book that never arrived; this is their third call.",
  "summary": "Robert Kim, caller ID matched, ZIP not verified. Third contact (2 in last 14 days), upset. Order 415930, The Covenant of Water by Abraham Verghese, hardcover, $32.00, placed Oct 28, shipped Oct 31 via USPS, now marked lost by carrier. Not returnable (lost in transit). Needs replacement or refund decision; nothing promised.",
  "customer": {
    "id": 5,
    "name": "Robert Kim",
    "phone_on_file": "+16175550188",
    "email": "robert.kim@example.com"
  },
  "caller_id": "+16175550188",
  "identified_via": "caller_id",
  "zip_verified": false,
  "selected_order": "415930",
  "actions_taken": [],
  "pending_unconfirmed_change": null
}
```

## End-of-call summary

```json
{
  "call_id": "sim-angry_transfer",
  "duration_s": 33.5,
  "caller_id": "+16175550188",
  "customer": "Robert Kim",
  "identified_via": "caller_id",
  "verification_level": "identified",
  "selected_order": "415930",
  "actions_taken": [],
  "end_reason": "transfer:angry_or_repeat_caller",
  "handoff": {
    "reason": "angry_or_repeat_caller",
    "caller_wants": "Caller wants resolution for a book that never arrived; this is their third call.",
    "summary": "Robert Kim, caller ID matched, ZIP not verified. Third contact (2 in last 14 days), upset. Order 415930, The Covenant of Water by Abraham Verghese, hardcover, $32.00, placed Oct 28, shipped Oct 31 via USPS, now marked lost by carrier. Not returnable (lost in transit). Needs replacement or refund decision; nothing promised.",
    "customer": {
      "id": 5,
      "name": "Robert Kim",
      "phone_on_file": "+16175550188",
      "email": "robert.kim@example.com"
    },
    "caller_id": "+16175550188",
    "identified_via": "caller_id",
    "zip_verified": false,
    "selected_order": "415930",
    "actions_taken": [],
    "pending_unconfirmed_change": null
  },
  "caller_turns": 1,
  "tool_calls": 2,
  "latency_ms": {
    "p50": 3381,
    "max": 3381
  }
}
```
