# Angry repeat caller with a lost order: immediate handoff

- **Persona:** `angry_transfer` · Robert Kim · caller ID `+16175550188`
- **Shows:** knowing when not to decide: escalation with a structured summary, no attempted fixes
- **Result:** PASS (9/9 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 3498 ms, max 3498 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "Robert Kim", "repeat_caller": true, "recent_contacts": 2}, "orders": [{"order_number": "415930", "placed_at": "Wednesday, October 28th", "items": [{"title": "The Covenant of Water", …`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** This is the third time I'm calling. My book never showed up and nobody has fixed it!

> `transfer_to_human` `{"reason": "angry_or_repeat_caller", "caller_wants": "Resolution for a book that never arrived; this is their third call.", "order_number": "415930", "summary":…` → `{"status": "transferring", "instruction": "Tell the caller in one sentence that you're connecting them with a specialist who will have these details, so they won't need to repeat themselves. Then stop."}`

**Bookly:** I'm sorry, Robert, I can see your order with The Covenant of Water was marked lost by the carrier, so I'm connecting you with a specialist now and passing along everything so you won't have to repeat yourself. _(3498 ms)_

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
  "caller_wants": "Resolution for a book that never arrived; this is their third call.",
  "summary": "Repeat caller Robert Kim (caller ID matched, ZIP not verified), 2 prior contacts in 14 days, frustrated. Order 415930, The Covenant of Water by Abraham Verghese, hardcover, $32.00, placed October 28th, shipped USPS October 31st, carrier marked it lost. Needs replacement or refund decision; nothing promised.",
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
  "duration_s": 33.2,
  "caller_id": "+16175550188",
  "customer": "Robert Kim",
  "identified_via": "caller_id",
  "verification_level": "identified",
  "selected_order": "415930",
  "actions_taken": [],
  "end_reason": "transfer:angry_or_repeat_caller",
  "handoff": {
    "reason": "angry_or_repeat_caller",
    "caller_wants": "Resolution for a book that never arrived; this is their third call.",
    "summary": "Repeat caller Robert Kim (caller ID matched, ZIP not verified), 2 prior contacts in 14 days, frustrated. Order 415930, The Covenant of Water by Abraham Verghese, hardcover, $32.00, placed October 28th, shipped USPS October 31st, carrier marked it lost. Needs replacement or refund decision; nothing promised.",
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
    "p50": 3498,
    "max": 3498
  }
}
```
