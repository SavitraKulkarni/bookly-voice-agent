# Angry repeat caller with a lost order: immediate handoff

- **Persona:** `angry_transfer` · Robert Kim · caller ID `+16175550188`
- **Shows:** knowing when not to decide: escalation with a structured summary, no attempted fixes
- **Result:** PASS (9/9 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 3866 ms, max 3866 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "Robert Kim", "repeat_caller": true, "recent_contacts": 2}, "orders": [{"order_number": "415930", "placed_at": "Thursday, October 29th", "items": [{"title": "The Covenant of Water", "…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** This is the third time I'm calling. My book never showed up and nobody has fixed it! I want to talk to a real person, not a bot.

> `transfer_to_human` `{"reason": "angry_or_repeat_caller", "caller_wants": "Caller wants to speak to a person about a book that never arrived; this is their third call.", "order_numb…` → `{"status": "transferring", "instruction": "Tell the caller in one sentence that you're connecting them with a specialist who will have these details, so they won't need to repeat themselves. Then stop."}`

**Bookly:** I'm sorry for the trouble. I'm connecting you with a specialist now and passing along everything so you won't have to repeat yourself. _(3866 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words (book titles/authors not counted), no markdown/URLs | ✅ |
| transferred | ✅ |
| reason is angry/repeat or lost | ✅ |
| handed off within 2 replies | ✅ |
| no writes attempted | ✅ |
| handoff summary identifies the order/book | ✅ |

## Handoff packet (what the human agent receives)

```json
{
  "reason": "angry_or_repeat_caller",
  "caller_wants": "Caller wants to speak to a person about a book that never arrived; this is their third call.",
  "summary": "Repeat caller (2 contacts in last 14 days), upset, requested a human. Caller ID matched Robert Kim; ZIP not verified. Order 415930 (placed Oct 29, shipped Nov 1 via USPS) contains The Covenant of Water by Abraham Verghese, hardcover, $32.00, and is marked lost by the carrier. Caller didn't name the order, but it's the only one on file. Unresolved: replacement or refund for the lost order.",
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
  "duration_s": 27.7,
  "caller_id": "+16175550188",
  "customer": "Robert Kim",
  "identified_via": "caller_id",
  "verification_level": "identified",
  "selected_order": "415930",
  "actions_taken": [],
  "end_reason": "transfer:angry_or_repeat_caller",
  "handoff": {
    "reason": "angry_or_repeat_caller",
    "caller_wants": "Caller wants to speak to a person about a book that never arrived; this is their third call.",
    "summary": "Repeat caller (2 contacts in last 14 days), upset, requested a human. Caller ID matched Robert Kim; ZIP not verified. Order 415930 (placed Oct 29, shipped Nov 1 via USPS) contains The Covenant of Water by Abraham Verghese, hardcover, $32.00, and is marked lost by the carrier. Caller didn't name the order, but it's the only one on file. Unresolved: replacement or refund for the lost order.",
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
    "p50": 3866,
    "max": 3866
  }
}
```
