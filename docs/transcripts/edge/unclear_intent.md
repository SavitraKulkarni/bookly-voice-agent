# Caller can't say what they need, even after one clarifying question

- **Persona:** `unclear_intent` · Daniel Reyes · caller ID `+12065550177`
- **Shows:** one clarifying question, then a clean handoff instead of guessing
- **Result:** PASS (7/7 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 2379 ms, max 3722 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "Daniel Reyes", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "416881", "placed_at": "Thursday, September 24th", "items": [{"title": "The Name of the Wind…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hi, yeah, I've got kind of a weird thing going on, with like, the account thing.

**Bookly:** No problem, Daniel, I can help sort it out. What's happening with your account? For example, are you having trouble signing in? _(1036 ms)_

**Caller:** It's hard to explain, it's just acting weird, you know?

> `transfer_to_human` `{"reason": "unclear_intent", "caller_wants": "Help with an account issue they describe as the account \"acting weird,\" details unclear.", "summary": "Caller Da…` → `{"status": "transferring", "instruction": "Tell the caller in one sentence that you're connecting them with a specialist who will have these details, so they won't need to repeat themselves. Then stop."}`

**Bookly:** I'm connecting you with a specialist who can dig into your account with you, and I'm passing along what you've told me so you won't have to repeat yourself. _(3722 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words, no markdown/URLs | ✅ |
| transferred: unclear_intent | ✅ |
| asked at most two questions first | ✅ |
| no writes | ✅ |

## Handoff packet (what the human agent receives)

```json
{
  "reason": "unclear_intent",
  "caller_wants": "Help with an account issue they describe as the account \"acting weird,\" details unclear.",
  "summary": "Caller Daniel Reyes identified by caller ID; ZIP not verified. Asked one clarifying question (e.g., sign-in trouble?) but caller couldn't specify the problem. Only order on file is 4 1 6 8 8 1 (The Name of the Wind by Patrick Rothfuss), delivered September 30th, not mentioned by caller. Issue unresolved.",
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
  "call_id": "sim-unclear_intent",
  "duration_s": 10.2,
  "caller_id": "+12065550177",
  "customer": "Daniel Reyes",
  "identified_via": "caller_id",
  "verification_level": "identified",
  "selected_order": null,
  "actions_taken": [],
  "end_reason": "transfer:unclear_intent",
  "handoff": {
    "reason": "unclear_intent",
    "caller_wants": "Help with an account issue they describe as the account \"acting weird,\" details unclear.",
    "summary": "Caller Daniel Reyes identified by caller ID; ZIP not verified. Asked one clarifying question (e.g., sign-in trouble?) but caller couldn't specify the problem. Only order on file is 4 1 6 8 8 1 (The Name of the Wind by Patrick Rothfuss), delivered September 30th, not mentioned by caller. Issue unresolved.",
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
  "caller_turns": 2,
  "tool_calls": 2,
  "latency_ms": {
    "p50": 2379,
    "max": 3722
  }
}
```
