# Unknown caller without an order number: email as last resort

- **Persona:** `email_fallback` · Maya Chen (calling from a work phone) · caller ID `+15125550199`
- **Shows:** identity ladder: caller ID, then order number, then email
- **Result:** PASS (8/8 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 1341 ms, max 3620 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": false, "message": "Caller ID doesn't match any account.", "guidance": "Ask for their order number; use email only as a last resort."}`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hi, yeah, I'm calling to check on an order I placed. It's The Alchemist, and I'm just wondering where it is.

**Bookly:** I can help with that. Since I couldn't match the number you're calling from, could you give me your order number? _(793 ms)_

**Caller:** Oh, I'm actually calling from my work phone, and I don't have the order number handy, sorry.

**Bookly:** No problem. What's the email address on your Bookly account? I can look it up that way. _(1030 ms)_

**Caller:** Sure, it's maya dot chen at example dot com.

> `lookup_customer` `{"method": "email", "email": "maya.chen@example.com"}` → `{"found": true, "customer": {"name": "Maya Chen", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "418355", "placed_at": "Thursday, November 19th", "items": [{"title": "The Alchemist", "author"…`

> `lookup_order` `{"order_number": "418355"}` → `{"customer_name": "Maya Chen", "order": {"order_number": "418355", "status": "shipped", "placed_at": "Thursday, November 19th", "shipped_at": "Saturday, November 21st", "delivered_at": null, "estimated_delivery": "Thursd…`

**Bookly:** I found your account from that email. Your order with The Alchemist by Paulo Coelho shipped with UPS and should arrive Thursday, November 26th. Would you like me to text you the tracking number? _(3620 ms)_

**Caller:** Oh great, no that's okay, Thursday works. Thanks, bye!

> `end_call` `{"reason": "resolved", "goodbye": "You're welcome, enjoy The Alchemist, and thanks for calling Bookly!"}` → `{"status": "ending", "instruction": "Say a one-sentence goodbye."}`

**Bookly:** You're welcome, enjoy The Alchemist, and thanks for calling Bookly! _(1652 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words (book titles/authors not counted), no markdown/URLs | ✅ |
| asked for order number before email | ✅ |
| identified by email | ✅ |
| gave the Alchemist status (shipped) | ✅ |
| no writes | ✅ |

## End-of-call summary

```json
{
  "call_id": "sim-email_fallback",
  "duration_s": 53.3,
  "caller_id": "+15125550199",
  "customer": "Maya Chen",
  "identified_via": "email",
  "verification_level": "identified",
  "selected_order": "418355",
  "actions_taken": [],
  "end_reason": "end:resolved",
  "handoff": null,
  "caller_turns": 4,
  "tool_calls": 4,
  "latency_ms": {
    "p50": 1341,
    "max": 3620
  }
}
```
