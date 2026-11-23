# Takes store credit, confirms, then immediately asks for a person

- **Persona:** `credit_then_person` · Maya Chen · caller ID `+14155550101`
- **Shows:** the credit promised 'right away' is on the account even though the call is handed off next
- **Result:** PASS (7/7 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 3331 ms, max 4024 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "Maya Chen", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "418355", "placed_at": "Wednesday, November 18th", "items": [{"title": "The Overstory", "author…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hi, I'd like to return a book I bought. It's Tomorrow, and Tomorrow, and Tomorrow by Gabrielle Zevin.

**Bookly:** I can help with that: Tomorrow, and Tomorrow, and Tomorrow by Gabrielle Zevin from order 4 1 8 0 2 7, which can still be returned. May I ask why you're returning it? _(1850 ms)_

**Caller:** Yeah, I just didn't really like it.

**Bookly:** That's fine. To make changes, I need to verify the ZIP code on the account. What's your ZIP? _(1787 ms)_

**Caller:** It's 94110.

> `verify_zip` `{"zip": "94110"}` → `{"verified": true}`

**Bookly:** Thanks, the ZIP is verified. I can add store credit of twenty-seven ninety-nine to your account right away, or refund it to your original payment once we receive the book. Would store credit work? _(2998 ms)_

**Caller:** Store credit works for me.

> `start_return` `{"order_number": "418027", "item_id": 2, "reason": "didn't like it", "resolution": "store_credit"}` → `{"status": "needs_confirmation", "read_back": "Return Tomorrow, and Tomorrow, and Tomorrow by Gabrielle Zevin from order 418027, $27.99 in store credit added to the account right away.", "instruction": "Read this back to…`

**Bookly:** Just to confirm: a return of Tomorrow, and Tomorrow, and Tomorrow by Gabrielle Zevin from order 4 1 8 0 2 7, with twenty-seven ninety-nine in store credit added to your account right away. Shall I go ahead? _(3665 ms)_

**Caller:** Yes, go ahead.

> `start_return` `{"order_number": "418027", "item_id": 2, "reason": "didn't like it", "resolution": "store_credit", "confirmed": true}` → `{"status": "return_started", "return_id": 1, "resolution": "store_credit", "amount": "$27.99", "next_steps": "A prepaid return label has been emailed to the address on file. $27.99 in store credit is on the account now."…`

**Bookly:** I've started your return, and twenty-seven ninety-nine in store credit is on your account now. We've emailed a prepaid return label to the address on file. Would you like a receipt by text or email? _(3791 ms)_

**Caller:** Email's fine. Thanks. Actually, can I talk to a person about something else?

> `send_confirmation` `{"kind": "receipt", "channel": "email", "order_number": "418027"}` → `{"status": "sent", "channel": "email", "to": "maya.chen@example.com", "mock": true, "note": "Delivery is mocked (written to the outbox)."}`

> `transfer_to_human` `{"reason": "caller_requested", "caller_wants": "Caller asked to speak with a person about a different, unspecified matter.", "summary": "Caller ID matched, ZIP …` → `{"status": "transferring", "instruction": "Tell the caller in one sentence that you're connecting them with a specialist who will have these details, so they won't need to repeat themselves. Then stop."}`

**Bookly:** Your receipt is on its way by email, and I'm connecting you with a person now and passing along everything so you won't have to repeat yourself. _(4024 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words (book titles/authors not counted), no markdown/URLs | ✅ |
| credit on the account ($27.99) | ✅ |
| no unpaid store-credit return | ✅ |
| transferred | ✅ |

## Handoff packet (what the human agent receives)

```json
{
  "reason": "caller_requested",
  "caller_wants": "Caller asked to speak with a person about a different, unspecified matter.",
  "summary": "Caller ID matched, ZIP verified. Return 1 completed for Tomorrow, and Tomorrow, and Tomorrow by Gabrielle Zevin from order 418027 (didn't like it); $27.99 store credit issued, prepaid label emailed, receipt emailed. New topic not yet stated.",
  "customer": {
    "id": 1,
    "name": "Maya Chen",
    "phone_on_file": "+14155550101",
    "email": "maya.chen@example.com"
  },
  "caller_id": "+14155550101",
  "identified_via": "caller_id",
  "zip_verified": true,
  "selected_order": "418027",
  "actions_taken": [
    "return #1: Tomorrow, and Tomorrow, and Tomorrow by Gabrielle Zevin (store_credit, $27.99)"
  ],
  "pending_unconfirmed_change": null
}
```

## End-of-call summary

```json
{
  "call_id": "sim-credit_then_person",
  "duration_s": 34.9,
  "caller_id": "+14155550101",
  "customer": "Maya Chen",
  "identified_via": "caller_id",
  "verification_level": "zip_verified",
  "selected_order": "418027",
  "actions_taken": [
    "return #1: Tomorrow, and Tomorrow, and Tomorrow by Gabrielle Zevin (store_credit, $27.99)"
  ],
  "end_reason": "transfer:caller_requested",
  "handoff": {
    "reason": "caller_requested",
    "caller_wants": "Caller asked to speak with a person about a different, unspecified matter.",
    "summary": "Caller ID matched, ZIP verified. Return 1 completed for Tomorrow, and Tomorrow, and Tomorrow by Gabrielle Zevin from order 418027 (didn't like it); $27.99 store credit issued, prepaid label emailed, receipt emailed. New topic not yet stated.",
    "customer": {
      "id": 1,
      "name": "Maya Chen",
      "phone_on_file": "+14155550101",
      "email": "maya.chen@example.com"
    },
    "caller_id": "+14155550101",
    "identified_via": "caller_id",
    "zip_verified": true,
    "selected_order": "418027",
    "actions_taken": [
      "return #1: Tomorrow, and Tomorrow, and Tomorrow by Gabrielle Zevin (store_credit, $27.99)"
    ],
    "pending_unconfirmed_change": null
  },
  "caller_turns": 6,
  "tool_calls": 6,
  "latency_ms": {
    "p50": 3331,
    "max": 4024
  }
}
```
