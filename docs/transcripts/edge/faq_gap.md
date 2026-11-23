# Question the FAQ doesn't cover

- **Persona:** `faq_gap` · James Okafor · caller ID `+13125550142`
- **Shows:** says 'I don't know' instead of inventing a policy; offers a person
- **Result:** PASS (7/7 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 1509 ms, max 2361 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "James Okafor", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "419120", "placed_at": "Thursday, November 19th", "items": [{"title": "Project Hail Mary", "…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hey, yeah, do you guys have a student discount? Like ten percent off or something?

> `search_faq` `{"query": "student discount"}` → `{"found": false, "guidance": "The FAQ doesn't cover this. Say you don't have that answer and offer a transfer. Don't answer from general knowledge."}`

**Bookly:** I'm afraid I can't tell you whether we have a student discount. Would you like me to connect you with someone who can check? _(2361 ms)_

**Caller:** Are you sure? Most stores do.

**Bookly:** I get why you'd expect one, but I don't have anything about a student discount, so I can't say yes or no. A person could check for you. Would you like me to transfer you? _(1509 ms)_

**Caller:** Nah, that's okay, no thanks. I'll just check the website or something. Bye.

> `end_call` `{"reason": "resolved", "goodbye": "No problem, thanks for calling Bookly, and have a great day!"}` → `{"status": "ending", "instruction": "Say a one-sentence goodbye."}`

**Bookly:** No problem, thanks for calling Bookly, and have a great day! _(1235 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words (book titles/authors not counted), no markdown/URLs | ✅ |
| searched the FAQ | ✅ |
| no invented discount | ✅ |
| offered a person | ✅ |

## End-of-call summary

```json
{
  "call_id": "sim-faq_gap",
  "duration_s": 45.3,
  "caller_id": "+13125550142",
  "customer": "James Okafor",
  "identified_via": "caller_id",
  "verification_level": "identified",
  "selected_order": null,
  "actions_taken": [],
  "end_reason": "end:resolved",
  "handoff": null,
  "caller_turns": 3,
  "tool_calls": 3,
  "latency_ms": {
    "p50": 1509,
    "max": 2361
  }
}
```
