# Return outside the 30-day window: state policy, no exception, hand off

- **Persona:** `outside_window` · Daniel Reyes · caller ID `+12065550177`
- **Shows:** policy stated without negotiating, escalation with structured handoff
- **Result:** PASS (9/9 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 2805 ms, max 3480 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "Daniel Reyes", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "416881", "placed_at": "2026-09-24", "items": [{"title": "The Name of the Wind", "author": "…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hi, yeah, I'd like to return a book I bought, The Name of the Wind by Patrick Rothfuss. I just didn't really like it.

**Bookly:** Got it, The Name of the Wind by Patrick Rothfuss from order 4 1 6 8 8 1. That order was delivered on Wednesday, September 30th, which is past our 30-day return window. Would you like me to transfer you to a specialist? _(2131 ms)_

**Caller:** Oh, really? It's only a few weeks late, can't you make an exception?

> `transfer_to_human` `{"reason": "outside_policy", "caller_wants": "Caller wants an exception to return The Name of the Wind by Patrick Rothfuss outside the 30-day window because he …` → `{"status": "transferring", "instruction": "Tell the caller in one sentence that you're connecting them with a specialist who will have these details, so they won't need to repeat themselves. Then stop."}`

**Bookly:** I can't make exceptions myself, so I'm connecting you with a specialist and passing along everything so you won't have to repeat yourself. _(3480 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words, no markdown/URLs | ✅ |
| order 416881 data from the system | ✅ |
| stated the 30-day policy | ✅ |
| no return created | ✅ |
| transferred: outside_policy | ✅ |
| handoff names the order | ✅ |

## Handoff packet (what the human agent receives)

```json
{
  "reason": "outside_policy",
  "caller_wants": "Caller wants an exception to return The Name of the Wind by Patrick Rothfuss outside the 30-day window because he didn't like it.",
  "summary": "Caller identified via caller ID (Daniel Reyes); ZIP not verified. Order 416881, one item: The Name of the Wind by Patrick Rothfuss, paperback, $19.99 (item_id 6). Delivered Sept 30, 2026; return window ended Oct 30, 2026 (52 days since delivery), so not returnable per policy. Reason: didn't like the book. Caller asked for an exception; unresolved whether one will be granted.",
  "customer": {
    "id": 3,
    "name": "Daniel Reyes",
    "phone_on_file": "+12065550177",
    "email": "daniel.reyes@example.com"
  },
  "caller_id": "+12065550177",
  "identified_via": "caller_id",
  "zip_verified": false,
  "selected_order": "416881",
  "actions_taken": [],
  "pending_unconfirmed_change": null
}
```

## End-of-call summary

```json
{
  "call_id": "sim-outside_window",
  "duration_s": 33.5,
  "caller_id": "+12065550177",
  "customer": "Daniel Reyes",
  "identified_via": "caller_id",
  "verification_level": "identified",
  "selected_order": "416881",
  "actions_taken": [],
  "end_reason": "transfer:outside_policy",
  "handoff": {
    "reason": "outside_policy",
    "caller_wants": "Caller wants an exception to return The Name of the Wind by Patrick Rothfuss outside the 30-day window because he didn't like it.",
    "summary": "Caller identified via caller ID (Daniel Reyes); ZIP not verified. Order 416881, one item: The Name of the Wind by Patrick Rothfuss, paperback, $19.99 (item_id 6). Delivered Sept 30, 2026; return window ended Oct 30, 2026 (52 days since delivery), so not returnable per policy. Reason: didn't like the book. Caller asked for an exception; unresolved whether one will be granted.",
    "customer": {
      "id": 3,
      "name": "Daniel Reyes",
      "phone_on_file": "+12065550177",
      "email": "daniel.reyes@example.com"
    },
    "caller_id": "+12065550177",
    "identified_via": "caller_id",
    "zip_verified": false,
    "selected_order": "416881",
    "actions_taken": [],
    "pending_unconfirmed_change": null
  },
  "caller_turns": 2,
  "tool_calls": 2,
  "latency_ms": {
    "p50": 2805,
    "max": 3480
  }
}
```
