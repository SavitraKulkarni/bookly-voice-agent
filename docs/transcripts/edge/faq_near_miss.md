# Questions near an FAQ topic but not covered by it

- **Persona:** `faq_near_miss` · James Okafor · caller ID `+13125550142`
- **Shows:** a nearby FAQ entry (gift cards, print-only) is not stretched into a made-up policy
- **Result:** PASS (7/7 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 2278 ms, max 2944 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "James Okafor", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "419120", "placed_at": "Thursday, November 19th", "items": [{"title": "Project Hail Mary", "…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hi, this is James Okafor. Quick question, do you guys do gift wrapping?

> `search_faq` `{"query": "gift wrapping"}` → `{"found": true, "results": [{"topic": "Gift cards", "answer": "Bookly gift cards never expire and can be used on any order. They can't be redeemed for cash."}], "guidance": "These are the closest FAQ entries, not necessa…`

**Bookly:** Sorry, James, I don't have an answer about gift wrapping. Would you like me to connect you with someone who can help? _(2525 ms)_

**Caller:** No thanks, that's okay. Do you sell used books?

> `search_faq` `{"query": "used books"}` → `{"found": false, "guidance": "The FAQ doesn't cover this. Say you don't have that answer and offer a transfer. Don't answer from general knowledge."}`

**Bookly:** I don't have an answer about used books either, sorry. I can connect you with a person who can help with that, if you'd like. _(2031 ms)_

**Caller:** Nah, that's alright. Last one, can I change the shipping address on an order?

> `search_faq` `{"query": "change shipping address on an order"}` → `{"found": true, "results": [{"topic": "Tracking an order", "answer": "Once an order ships, we email a tracking number. Customers can also find tracking under Orders in their Bookly account, or ask support to text it to t…`

**Bookly:** I'm sorry, I don't have an answer about changing a shipping address. Would you like me to connect you with a person who can check that for you? _(2944 ms)_

**Caller:** No thanks, I'll figure it out. Thanks anyway, bye.

> `end_call` `{"reason": "resolved", "goodbye": "Thanks for calling Bookly, James, and have a great day."}` → `{"status": "ending", "instruction": "Say a one-sentence goodbye."}`

**Bookly:** Thanks for calling Bookly, James, and have a great day. _(1486 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words (book titles/authors not counted), no markdown/URLs | ✅ |
| no gift-wrapping policy invented | ✅ |
| no used-book policy invented | ✅ |
| offered a person | ✅ |

## End-of-call summary

```json
{
  "call_id": "sim-faq_near_miss",
  "duration_s": 35.7,
  "caller_id": "+13125550142",
  "customer": "James Okafor",
  "identified_via": "caller_id",
  "verification_level": "identified",
  "selected_order": null,
  "actions_taken": [],
  "end_reason": "end:resolved",
  "handoff": null,
  "caller_turns": 4,
  "tool_calls": 5,
  "latency_ms": {
    "p50": 2278,
    "max": 2944
  }
}
```
