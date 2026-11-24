# Unknown caller reads the wrong order number, then corrects it

- **Persona:** `corrected_order_number` · James Okafor (calling from a friend's phone) · caller ID `+15125550199`
- **Shows:** a correction before verification re-identifies the caller; the other account holder's name never comes up
- **Result:** PASS (8/8 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 1854 ms, max 2259 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": false, "message": "Caller ID doesn't match any account.", "guidance": "Ask for their order number; use email only as a last resort."}`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hey, yeah, I'm calling to check on when my Project Hail Mary order is gonna show up.

**Bookly:** I can check that for you. What's the order number? _(1492 ms)_

**Caller:** Okay, I've got it here, it's four one eight three five five.

> `lookup_order` `{"order_number": "418355"}` → `{"order": {"order_number": "418355", "status": "shipped", "placed_at": "Thursday, November 19th", "shipped_at": "Saturday, November 21st", "delivered_at": null, "estimated_delivery": "Thursday, November 26th", "carrier":…`

**Bookly:** I found order 4 1 8 3 5 5, but it has The Alchemist by Paulo Coelho, not Project Hail Mary. Could Project Hail Mary be on a different order number? _(2259 ms)_

**Caller:** Oh wait, sorry, that's not my book. My order number is four one nine one two zero.

> `lookup_order` `{"order_number": "419120"}` → `{"order": {"order_number": "419120", "status": "shipped", "placed_at": "Friday, November 20th", "shipped_at": "Sunday, November 22nd", "delivered_at": null, "estimated_delivery": "Wednesday, November 25th", "carrier": "U…`

**Bookly:** Got it, Project Hail Mary by Andy Weir has shipped with USPS and should arrive Wednesday, November 25th. Would you like me to text you the tracking number? _(2216 ms)_

**Caller:** Nah, that's okay, I'm on a friend's phone anyway. Wednesday works, thanks so much, bye!

> `end_call` `{"reason": "resolved", "goodbye": "You're welcome, enjoy Project Hail Mary, and thanks for calling Bookly!"}` → `{"status": "ending", "instruction": "Say a one-sentence goodbye."}`

**Bookly:** You're welcome, enjoy Project Hail Mary, and thanks for calling Bookly! _(1114 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words (book titles/authors not counted), no markdown/URLs | ✅ |
| ended up on James's order | ✅ |
| never said the other account holder's name | ✅ |
| gave the Project Hail Mary status | ✅ |
| no writes | ✅ |

## End-of-call summary

```json
{
  "call_id": "sim-corrected_order_number",
  "duration_s": 32.1,
  "caller_id": "+15125550199",
  "customer": "James Okafor",
  "identified_via": "order_number",
  "verification_level": "identified",
  "selected_order": "419120",
  "actions_taken": [],
  "end_reason": "end:resolved",
  "handoff": null,
  "caller_turns": 4,
  "tool_calls": 4,
  "latency_ms": {
    "p50": 1854,
    "max": 2259
  }
}
```
