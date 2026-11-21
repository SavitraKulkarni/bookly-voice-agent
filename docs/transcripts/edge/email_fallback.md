# Unknown caller without an order number: email as last resort

- **Persona:** `email_fallback` · Maya Chen (calling from a work phone) · caller ID `+15125550199`
- **Shows:** identity ladder: caller ID, then order number, then email
- **Result:** PASS (8/8 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 1578 ms, max 4270 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": false, "message": "Caller ID doesn't match any account.", "guidance": "Ask for their order number; use email only as a last resort."}`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hi, I'm trying to find out where my order of The Overstory is. Can you check on that for me?

**Bookly:** Sure, I can check on that. What's the order number? _(936 ms)_

**Caller:** Oh, I don't have it handy right now, sorry. I'm calling from my work phone.

> `lookup_customer` `{"method": "caller_id"}` → `{"found": false, "message": "Caller ID doesn't match any account.", "guidance": "Ask for their order number; use email only as a last resort."}`

**Bookly:** No problem. What's the email address on your Bookly account? _(1948 ms)_

**Caller:** It's maya dot chen at example dot com.

> `lookup_customer` `{"method": "email", "email": "maya.chen@example.com"}` → `{"found": true, "customer": {"name": "Maya Chen", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "418355", "placed_at": "Tuesday, November 17th", "items": [{"title": "The Overstory", "author":…`

> `lookup_order` `{"order_number": "418355"}` → `{"customer_name": "Maya Chen", "order": {"order_number": "418355", "status": "shipped", "placed_at": "Tuesday, November 17th", "shipped_at": "Thursday, November 19th", "delivered_at": null, "estimated_delivery": "Tuesday…`

**Bookly:** Thanks, Maya. Your order with The Overstory by Richard Powers has shipped with UPS and should arrive Tuesday, November 24th. Would you like me to send you the tracking number? _(4270 ms)_

**Caller:** Nah, that's okay, Tuesday works. Thanks, bye!

> `end_call` `{"reason": "resolved", "goodbye": "You're welcome, Maya, enjoy The Overstory, and have a great weekend!"}` → `{"status": "ending", "instruction": "Say a one-sentence goodbye."}`

**Bookly:** You're welcome, Maya, enjoy The Overstory, and have a great weekend! _(1208 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words, no markdown/URLs | ✅ |
| asked for order number before email | ✅ |
| identified by email | ✅ |
| gave the Overstory status (shipped) | ✅ |
| no writes | ✅ |

## End-of-call summary

```json
{
  "call_id": "sim-email_fallback",
  "duration_s": 26.1,
  "caller_id": "+15125550199",
  "customer": "Maya Chen",
  "identified_via": "email",
  "verification_level": "identified",
  "selected_order": "418355",
  "actions_taken": [],
  "end_reason": "end:resolved",
  "handoff": null,
  "caller_turns": 4,
  "tool_calls": 5,
  "latency_ms": {
    "p50": 1578,
    "max": 4270
  }
}
```
