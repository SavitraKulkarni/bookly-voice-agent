# Caller asks for a person straight away

- **Persona:** `asks_for_human` · Daniel Reyes · caller ID `+12065550177`
- **Shows:** respects the request immediately, still passes context along
- **Result:** PASS (7/7 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 3682 ms, max 3682 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "Daniel Reyes", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "416881", "placed_at": "Saturday, September 26th", "items": [{"title": "The Name of the Wind…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Can I just talk to a real person, please?

> `transfer_to_human` `{"reason": "caller_requested", "caller_wants": "The caller asked to speak with a person right away; they didn't say why.", "summary": "Caller ID matched Daniel …` → `{"status": "transferring", "instruction": "Tell the caller in one sentence that you're connecting them with a specialist who will have these details, so they won't need to repeat themselves. Then stop."}`

**Bookly:** Of course, I'm connecting you with a person now and passing along your account details so you won't have to repeat yourself. _(3682 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words (book titles/authors not counted), no markdown/URLs | ✅ |
| transferred | ✅ |
| within two replies | ✅ |
| no writes | ✅ |

## Handoff packet (what the human agent receives)

```json
{
  "reason": "caller_requested",
  "caller_wants": "The caller asked to speak with a person right away; they didn't say why.",
  "summary": "Caller ID matched Daniel Reyes; ZIP not verified. One order on file: 416881, The Name of the Wind by Patrick Rothfuss, delivered Friday, October 2nd via UPS, outside the 30-day return window (ended Sunday, November 1st). The caller's reason for calling was not discussed and is unresolved.",
  "customer": {
    "id": 3,
    "name": "Daniel Reyes",
    "phone_on_file": "+12065550177",
    "email": "daniel.reyes@example.com"
  },
  "caller_id": "+12065550177",
  "identified_via": "caller_id",
  "zip_verified": false,
  "selected_order": null,
  "actions_taken": [],
  "pending_unconfirmed_change": null
}
```

## End-of-call summary

```json
{
  "call_id": "sim-asks_for_human",
  "duration_s": 35.8,
  "caller_id": "+12065550177",
  "customer": "Daniel Reyes",
  "identified_via": "caller_id",
  "verification_level": "identified",
  "selected_order": null,
  "actions_taken": [],
  "end_reason": "transfer:caller_requested",
  "handoff": {
    "reason": "caller_requested",
    "caller_wants": "The caller asked to speak with a person right away; they didn't say why.",
    "summary": "Caller ID matched Daniel Reyes; ZIP not verified. One order on file: 416881, The Name of the Wind by Patrick Rothfuss, delivered Friday, October 2nd via UPS, outside the 30-day return window (ended Sunday, November 1st). The caller's reason for calling was not discussed and is unresolved.",
    "customer": {
      "id": 3,
      "name": "Daniel Reyes",
      "phone_on_file": "+12065550177",
      "email": "daniel.reyes@example.com"
    },
    "caller_id": "+12065550177",
    "identified_via": "caller_id",
    "zip_verified": false,
    "selected_order": null,
    "actions_taken": [],
    "pending_unconfirmed_change": null
  },
  "caller_turns": 1,
  "tool_calls": 2,
  "latency_ms": {
    "p50": 3682,
    "max": 3682
  }
}
```
