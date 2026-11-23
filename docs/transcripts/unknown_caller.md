# Unknown caller: order number, then ZIP to cancel a processing order

- **Persona:** `unknown_caller` · Sofia Alvarez (calling from an unknown number) · caller ID `+15125550199`
- **Shows:** identity scales with risk (order number for read, + ZIP for write), processing → cancel
- **Result:** PASS (11/11 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 3383 ms, max 6617 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": false, "message": "Caller ID doesn't match any account.", "guidance": "Ask for their order number; use email only as a last resort."}`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hi, yeah, I'm calling to check on an order I placed for Lessons in Chemistry. Can you tell me where it's at?

**Bookly:** I can help with that. What's the order number? _(1098 ms)_

**Caller:** Sure, it's 420044.

> `lookup_order` `{"order_number": "420044"}` → `{"order": {"order_number": "420044", "status": "processing", "placed_at": "Saturday, November 21st", "shipped_at": null, "delivered_at": null, "estimated_delivery": "Saturday, November 28th", "carrier": null, "has_tracki…`

**Bookly:** Order 4 2 0 0 4 4, with Lessons in Chemistry by Bonnie Garmus, hasn't shipped yet. It's estimated to arrive Saturday, November 28th, and you can still cancel it if you'd like. Anything else I can help with? _(3383 ms)_

**Caller:** Oh good, actually I'd like to cancel it then. I found a copy at a local shop.

**Bookly:** Sure. To make changes, I need to verify the ZIP code on the account. What's your ZIP? _(1468 ms)_

**Caller:** Yeah, it's 11215.

> `verify_zip` `{"zip": "11215"}` → `{"verified": true}`

> `cancel_order` `{"order_number": "420044"}` → `{"status": "needs_confirmation", "read_back": "Cancel order 420044 (Lessons in Chemistry by Bonnie Garmus). The $29.99 charge will be released to the original payment method.", "instruction": "Read this back to the calle…`

**Bookly:** Thanks, that's verified. Just to confirm: cancel order 4 2 0 0 4 4 for Lessons in Chemistry by Bonnie Garmus, and the twenty-nine ninety-nine charge will be released to your original payment method. Shall I go ahead? _(6617 ms)_

**Caller:** Yes, go ahead.

> `cancel_order` `{"order_number": "420044", "confirmed": true}` → `{"status": "cancelled", "order_number": "420044", "next_steps": "The $29.99 authorisation is released within 3 to 5 business days."}`

**Bookly:** I've cancelled the order, and the twenty-nine ninety-nine charge will be released within 3 to 5 business days. Would you like a receipt by text or email? _(3501 ms)_

**Caller:** Email, please.

> `send_confirmation` `{"kind": "receipt", "channel": "email", "order_number": "420044"}` → `{"status": "sent", "channel": "email", "to": "sofia.alvarez@example.com", "mock": true, "note": "Delivery is mocked (written to the outbox)."}`

**Bookly:** I've sent the receipt to the email address we have on file. Is there anything else I can help with? _(3450 ms)_

**Caller:** Nope, that's everything. Thanks so much, bye!

> `end_call` `{"reason": "resolved", "goodbye": "You're welcome, enjoy the book, and have a great day!"}` → `{"status": "ending", "instruction": "Say a one-sentence goodbye."}`

**Bookly:** You're welcome, enjoy the book, and have a great day! _(1707 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words (book titles/authors not counted), no markdown/URLs | ✅ |
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
  "duration_s": 27.7,
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
    "p50": 3383,
    "max": 6617
  }
}
```
