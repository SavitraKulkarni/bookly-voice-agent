# Unknown caller reads the wrong order number, then corrects it

- **Persona:** `corrected_order_number` · James Okafor (calling from a friend's phone) · caller ID `+15125550199`
- **Shows:** a correction before verification re-identifies the caller; the other account holder's name never comes up
- **Result:** PASS (8/8 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 2016 ms, max 2660 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": false, "message": "Caller ID doesn't match any account.", "guidance": "Ask for their order number; use email only as a last resort."}`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hey, yeah, I'm just trying to find out when my order's gonna show up. It's Project Hail Mary.

**Bookly:** I can check that for you. What's your order number? _(710 ms)_

**Caller:** Uh, let me see here... it's four one eight three five five.

> `lookup_order` `{"order_number": "418355"}` → `{"order": {"order_number": "418355", "status": "shipped", "placed_at": "Wednesday, November 18th", "shipped_at": "Friday, November 20th", "delivered_at": null, "estimated_delivery": "Wednesday, November 25th", "carrier":…`

**Bookly:** I found order 4 1 8 3 5 5, but the book on it is The Overstory by Richard Powers, not Project Hail Mary. Could you double-check the order number for Project Hail Mary? _(2575 ms)_

**Caller:** Oh wait, sorry, that's not my book. My order number is four one nine one two zero.

> `lookup_order` `{"order_number": "419120"}` → `{"order": {"order_number": "419120", "status": "shipped", "placed_at": "Thursday, November 19th", "shipped_at": "Saturday, November 21st", "delivered_at": null, "estimated_delivery": "Tuesday, November 24th", "carrier": …`

**Bookly:** I found it: order 4 1 9 1 2 0 with Project Hail Mary by Andy Weir. It shipped with USPS, and it should arrive by Tuesday, November 24th. Want me to text you the tracking number? _(2660 ms)_

**Caller:** Nah, that's okay, I'm on a friend's phone anyway. Tuesday works, thanks a lot. Bye!

> `end_call` `{"reason": "resolved", "goodbye": "You're welcome, enjoy Project Hail Mary, and have a great day!"}` → `{"status": "ending", "instruction": "Say a one-sentence goodbye."}`

**Bookly:** You're welcome, enjoy Project Hail Mary, and have a great day! _(1457 ms)_

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
  "duration_s": 39.4,
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
    "p50": 2016,
    "max": 2660
  }
}
```
