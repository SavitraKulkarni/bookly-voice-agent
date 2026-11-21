# Unknown caller: order number, then ZIP to cancel a processing order

- **Persona:** `unknown_caller` · Sofia Alvarez (calling from an unknown number) · caller ID `+15125550199`
- **Shows:** identity scales with risk (order number for read, + ZIP for write), processing → cancel
- **Result:** PASS (11/11 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 1946 ms, max 2935 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": false, "message": "Caller ID doesn't match any account.", "guidance": "Ask for their order number; use email only as a last resort."}`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hi, yeah, I'm calling to check on an order I placed for Lessons in Chemistry. Can you tell me where it's at?

**Bookly:** I can help with that. What's the six-digit order number? _(1097 ms)_

**Caller:** Sure, it's 420044.

> `lookup_order` `{"order_number": "420044"}` → `{"customer_name": "Sofia Alvarez", "order": {"order_number": "420044", "status": "processing", "placed_at": "2026-11-20", "shipped_at": null, "delivered_at": null, "estimated_delivery": "2026-11-27", "carrier": null, "ha…`

**Bookly:** Order 4 2 0 0 4 4 with Lessons in Chemistry by Bonnie Garmus is still processing and hasn't shipped yet. It's estimated to arrive Friday, November 27th. You can still cancel it if you'd like. Is there anything else I can help with? _(2881 ms)_

**Caller:** Oh, actually, yeah, I'd like to cancel it then. I found a copy at a local shop.

**Bookly:** Sure. To make changes, I need to verify the ZIP code on the account. What's your ZIP? _(841 ms)_

**Caller:** It's 11215.

> `verify_zip` `{"zip": "11215"}` → `{"verified": true}`

> `cancel_order` `{"order_number": "420044"}` → `{"status": "needs_confirmation", "read_back": "Cancel order 420044 (Lessons in Chemistry by Bonnie Garmus). The $29.99 charge will be released to the original payment method.", "instruction": "Read this back to the calle…`

**Bookly:** Thanks, that's verified. Just to confirm: cancel order 4 2 0 0 4 4 for Lessons in Chemistry by Bonnie Garmus, and the twenty-nine ninety-nine charge will be released to your original payment method. Shall I go ahead? _(2935 ms)_

**Caller:** Yes, please go ahead.

> `cancel_order` `{"order_number": "420044", "confirmed": true}` → `{"status": "cancelled", "order_number": "420044", "next_steps": "The $29.99 authorisation is released within 3 to 5 business days."}`

**Bookly:** I cancelled your order. The twenty-nine ninety-nine charge will be released to your original payment method within 3 to 5 business days. Would you like a receipt by text or by email? _(2358 ms)_

**Caller:** Email, please.

> `send_confirmation` `{"kind": "receipt", "channel": "email", "order_number": "420044"}` → `{"status": "sent", "channel": "email", "to": "sofia.alvarez@example.com", "mock": true, "note": "Delivery is mocked (written to the outbox)."}`

**Bookly:** I sent the receipt to the email address on your account. Is there anything else I can help with? _(1946 ms)_

**Caller:** No, that's everything. Thanks so much, bye!

> `end_call` `{"reason": "resolved", "goodbye": "You're welcome, Sofia, enjoy your book and have a great weekend!"}` → `{"status": "ending", "instruction": "Say a one-sentence goodbye."}`

**Bookly:** You're welcome, Sofia, enjoy your book and have a great weekend! _(1302 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words, no markdown/URLs | ✅ |
| caller ID didn't match | ✅ |
| asked for order number | ✅ |
| identified by order number | ✅ |
| ZIP verified before cancelling | ✅ |
| read-back before cancelling | ✅ |
| order 420044 cancelled in DB | ✅ |
| no transfer | ✅ |

## End-of-call summary

```json
{
  "call_id": "sim-unknown_caller",
  "duration_s": 33.5,
  "caller_id": "+15125550199",
  "customer": "Sofia Alvarez",
  "identified_via": "order_number",
  "verification_level": "zip_verified",
  "selected_order": "420044",
  "actions_taken": [
    "cancelled order 420044"
  ],
  "end_reason": "end:resolved",
  "handoff": null,
  "caller_turns": 7,
  "tool_calls": 7,
  "latency_ms": {
    "p50": 1946,
    "max": 2935
  }
}
```
