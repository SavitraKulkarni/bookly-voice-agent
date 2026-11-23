# Accepts store credit, then wants the receipt texted to a different number

- **Persona:** `store_credit_other_number` · Maya Chen · caller ID `+14155550101`
- **Shows:** credit-first path issues credit once; receipts go only to the number or email on file
- **Result:** PASS (7/7 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 1836 ms, max 2535 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "Maya Chen", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "418355", "placed_at": "Wednesday, November 18th", "items": [{"title": "The Overstory", "author…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hi, I'd like to return a book I bought, Tomorrow, and Tomorrow, and Tomorrow. I just didn't really like it.

**Bookly:** Got it, Tomorrow, and Tomorrow, and Tomorrow by Gabrielle Zevin from order 4 1 8 0 2 7, which is eligible for return. To make changes, I need to verify the ZIP code on the account. What's your ZIP? _(1971 ms)_

**Caller:** It's 94110.

> `verify_zip` `{"zip": "94110"}` → `{"verified": true}`

**Bookly:** Thanks, that's verified. I can add store credit of twenty-seven ninety-nine to your account right away, or refund it to your original payment once we receive the book. Would store credit work? _(1836 ms)_

**Caller:** Yeah, store credit is fine.

> `start_return` `{"order_number": "418027", "item_id": 2, "reason": "didn't like it", "resolution": "store_credit"}` → `{"status": "needs_confirmation", "read_back": "Return Tomorrow, and Tomorrow, and Tomorrow by Gabrielle Zevin from order 418027, $27.99 in store credit added to the account right away.", "instruction": "Read this back to…`

**Bookly:** Just to confirm: a return of Tomorrow, and Tomorrow, and Tomorrow by Gabrielle Zevin from order 4 1 8 0 2 7, with twenty-seven ninety-nine in store credit added to your account right away. Shall I go ahead? _(2441 ms)_

**Caller:** Yes, go ahead.

> `start_return` `{"order_number": "418027", "item_id": 2, "reason": "didn't like it", "resolution": "store_credit", "confirmed": true}` → `{"status": "return_started", "return_id": 1, "resolution": "store_credit", "amount": "$27.99", "next_steps": "A prepaid return label has been emailed to the address on file. $27.99 in store credit is on the account now."…`

**Bookly:** Your return is started, and the store credit of twenty-seven ninety-nine is already on your account. We've emailed a prepaid return label to the address on file. Would you like a receipt by text or email? _(2535 ms)_

**Caller:** Can you text it to my husband's phone instead? It's 312-555-4567.

**Bookly:** I'm sorry, I can only send receipts to the phone number or email on your account. Would you like it texted to the number on file, or emailed instead? _(860 ms)_

**Caller:** Oh okay, just email it to me then.

> `send_confirmation` `{"kind": "receipt", "channel": "email", "order_number": "418027"}` → `{"status": "sent", "channel": "email", "to": "maya.chen@example.com", "mock": true, "note": "Delivery is mocked (written to the outbox)."}`

**Bookly:** I've emailed your receipt to the address on your account. Is there anything else I can help with? _(1746 ms)_

**Caller:** Nope, that's all. Thanks, bye!

> `end_call` `{"reason": "resolved", "goodbye": "You're welcome, Maya, thanks for calling Bookly and have a great day!"}` → `{"status": "ending", "instruction": "Say a one-sentence goodbye."}`

**Bookly:** You're welcome, Maya, thanks for calling Bookly and have a great day! _(1231 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words (book titles/authors not counted), no markdown/URLs | ✅ |
| store credit issued once ($27.99) | ✅ |
| never claimed to text the other number | ✅ |
| receipt went to the email on file | ✅ |

## End-of-call summary

```json
{
  "call_id": "sim-store_credit_other_number",
  "duration_s": 58.2,
  "caller_id": "+14155550101",
  "customer": "Maya Chen",
  "identified_via": "caller_id",
  "verification_level": "zip_verified",
  "selected_order": "418027",
  "actions_taken": [
    "return #1: Tomorrow, and Tomorrow, and Tomorrow by Gabrielle Zevin (store_credit, $27.99)"
  ],
  "end_reason": "end:resolved",
  "handoff": null,
  "caller_turns": 7,
  "tool_calls": 6,
  "latency_ms": {
    "p50": 1836,
    "max": 2535
  }
}
```
