# Question the FAQ doesn't cover

- **Persona:** `faq_gap` · James Okafor · caller ID `+13125550142`
- **Shows:** says 'I don't know' instead of inventing a policy; offers a person
- **Result:** PASS (7/7 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 3582 ms, max 3967 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "James Okafor", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "419120", "placed_at": "Friday, November 20th", "items": [{"title": "Project Hail Mary", "au…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hey, do you guys have a student discount? Like ten percent off or something?

> `search_faq` `{"query": "student discount"}` → `{"found": false, "guidance": "The FAQ doesn't cover this. Say you don't have that answer and offer a transfer. Don't answer from general knowledge."}`

**Bookly:** I'm sorry, I don't have an answer about student discounts. Would you like me to connect you with someone who can help with that? _(3967 ms)_

**Caller:** Are you sure? Most stores do.

> `search_faq` `{"query": "discounts promo codes coupons"}` → `{"found": false, "guidance": "The FAQ doesn't cover this. Say you don't have that answer and offer a transfer. Don't answer from general knowledge."}`

**Bookly:** I checked again, and I still can't find anything about student discounts or promo codes, so I can't say either way. Would you like me to connect you with someone who can check for you? _(3582 ms)_

**Caller:** Nah, that's okay, no thanks. Bye.

> `end_call` `{"reason": "caller_left", "goodbye": "No problem, thanks for calling Bookly, and have a great day!"}` → `{"status": "ending", "instruction": "Say a one-sentence goodbye."}`

**Bookly:** No problem, thanks for calling Bookly, and have a great day! _(2133 ms)_

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
  "duration_s": 40.3,
  "caller_id": "+13125550142",
  "customer": "James Okafor",
  "identified_via": "caller_id",
  "verification_level": "identified",
  "selected_order": null,
  "actions_taken": [],
  "end_reason": "end:caller_left",
  "handoff": null,
  "caller_turns": 3,
  "tool_calls": 4,
  "latency_ms": {
    "p50": 3582,
    "max": 3967
  }
}
```
