# Return: store credit offered once, declined, refund issued

- **Persona:** `return_credit_declined` · Maya Chen · caller ID `+14155550101`
- **Shows:** multi-turn info collection, ZIP step-up for writes, credit-first offer, read-back + confirm, idempotent write, receipt
- **Result:** PASS (12/12 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 2346 ms, max 3230 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "Maya Chen", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "418355", "placed_at": "Tuesday, November 17th", "items": [{"title": "The Overstory", "author":…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hi, yeah, I'd like to return a book. I got Klara and the Sun twice as a gift, so I don't need the second copy.

**Bookly:** Got it, Klara and the Sun by Kazuo Ishiguro from order 4 1 8 0 2 7, and it's eligible for return. To make changes, I need to verify the ZIP code on the account. What's your ZIP? _(1124 ms)_

**Caller:** Sure, it's 94110.

> `verify_zip` `{"zip": "94110"}` → `{"verified": true}`

**Bookly:** Thanks, that ZIP checks out. I can add store credit of fourteen ninety-nine to your account right away, or refund it to your original payment once we receive the book. Would store credit work? _(2527 ms)_

**Caller:** No thanks, I'd rather have a refund.

> `start_return` `{"order_number": "418027", "item_id": 1, "reason": "Received duplicate copy as a gift", "resolution": "refund"}` → `{"status": "needs_confirmation", "read_back": "Return Klara and the Sun by Kazuo Ishiguro from order 418027, refunded $14.99 to the original payment method once we receive the book.", "instruction": "Read this back to th…`

**Bookly:** No problem, a refund it is. Just to confirm: a return of Klara and the Sun by Kazuo Ishiguro from order 4 1 8 0 2 7, with fourteen ninety-nine refunded to your original payment once we receive the book. Shall I go ahead? _(2858 ms)_

**Caller:** Yes, that sounds right. Go ahead.

> `start_return` `{"order_number": "418027", "item_id": 1, "reason": "Received duplicate copy as a gift", "resolution": "refund", "confirmed": true}` → `{"status": "return_started", "return_id": 1, "resolution": "refund", "amount": "$14.99", "next_steps": "A prepaid return label is emailed to the address on file. Refund issues 5 to 7 business days after we receive the bo…`

**Bookly:** I've started your return. We'll email a prepaid return label to the address on file, and your refund will arrive 5 to 7 business days after we receive the book. Would you like a receipt by text or email? _(3230 ms)_

**Caller:** Text, please.

> `send_confirmation` `{"kind": "receipt", "channel": "sms", "order_number": "418027"}` → `{"status": "sent", "channel": "sms", "to": "***-***-0101", "mock": true, "note": "Delivery is mocked (written to the outbox)."}`

**Bookly:** I've texted the receipt to your number on file. Is there anything else I can help with? _(2166 ms)_

**Caller:** Nope, that's everything. Thanks so much, bye!

> `end_call` `{"reason": "resolved", "goodbye": "You're welcome, Maya, enjoy your books and have a great day!"}` → `{"status": "ending", "instruction": "Say a one-sentence goodbye."}`

**Bookly:** You're welcome, Maya, enjoy your books and have a great day! _(1460 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words, no markdown/URLs | ✅ |
| ZIP verified before the return | ✅ |
| read-back before executing | ✅ |
| store credit offered before refund | ✅ |
| credit offered only once | ✅ |
| refund recorded for Klara and the Sun (item 1) | ✅ |
| no store credit issued | ✅ |
| receipt texted | ✅ |
| no transfer | ✅ |

## End-of-call summary

```json
{
  "call_id": "sim-return_credit_declined",
  "duration_s": 33.2,
  "caller_id": "+14155550101",
  "customer": "Maya Chen",
  "identified_via": "caller_id",
  "verification_level": "zip_verified",
  "selected_order": "418027",
  "actions_taken": [
    "return #1: Klara and the Sun by Kazuo Ishiguro (refund, $14.99)"
  ],
  "end_reason": "end:resolved",
  "handoff": null,
  "caller_turns": 6,
  "tool_calls": 6,
  "latency_ms": {
    "p50": 2346,
    "max": 3230
  }
}
```
