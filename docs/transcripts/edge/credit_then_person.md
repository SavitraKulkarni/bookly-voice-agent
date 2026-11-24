# Takes store credit, confirms, then immediately asks for a person

- **Persona:** `credit_then_person` · Maya Chen · caller ID `+14155550101`
- **Shows:** the credit promised 'right away' is on the account even though the call is handed off next
- **Result:** PASS (7/7 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 3309 ms, max 5754 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "Maya Chen", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "418355", "placed_at": "Thursday, November 19th", "items": [{"title": "The Alchemist", "author"…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hi, I'd like to return a book I bought. It's Dune by Frank Herbert, I just didn't like it.

**Bookly:** I found your account from the number you're calling from, and Dune by Frank Herbert can be returned. To make changes, I need to verify the ZIP code on the account. What's your ZIP? _(1051 ms)_

**Caller:** It's 94110.

> `verify_zip` `{"zip": "94110"}` → `{"verified": true}`

**Bookly:** Thanks, you're verified. I can add store credit of twenty-seven ninety-nine to your account right away, or refund it to your original payment once we receive the book. Would store credit work? _(3309 ms)_

**Caller:** Yeah, store credit works for me.

> `start_return` `{"order_number": "418027", "item_id": 2, "reason": "didn't like it", "resolution": "store_credit"}` → `{"status": "needs_confirmation", "read_back": "Return Dune by Frank Herbert from order 418027, $27.99 in store credit added to the account right away.", "instruction": "Read this back to the caller and ask for a clear ye…`

**Bookly:** Just to confirm: a return of Dune, with twenty-seven ninety-nine in store credit added to your account right away. Shall I go ahead? _(3304 ms)_

**Caller:** Yes, go ahead.

> `start_return` `{"order_number": "418027", "item_id": 2, "reason": "didn't like it", "resolution": "store_credit", "confirmed": true}` → `{"status": "return_started", "return_id": 1, "resolution": "store_credit", "amount": "$27.99", "next_steps": "A prepaid return label has been emailed to the address on file. $27.99 in store credit is on the account now."…`

**Bookly:** Your return is started, and the twenty-seven ninety-nine in store credit is on your account now. We've emailed a prepaid return label to the address on file. Would you like a receipt by text or email? _(3701 ms)_

**Caller:** Email's fine, thanks. Actually, can I talk to a person about something else?

> `send_confirmation` `{"kind": "receipt", "channel": "email", "order_number": "418027"}` → `{"status": "sent", "channel": "email", "to": "maya.chen@example.com", "mock": true, "note": "Delivery is mocked (written to the outbox)."}`

> `transfer_to_human` `{"reason": "caller_requested", "caller_wants": "The caller asked to speak with a person about something other than her return, and didn't say what.", "summary":…` → `{"status": "transferring", "instruction": "Tell the caller in one sentence that you're connecting them with a specialist who will have these details, so they won't need to repeat themselves. Then stop."}`

**Bookly:** Your receipt is on its way to your email, and I'm connecting you with a person now and passing along everything so you won't have to repeat yourself. _(5754 ms)_

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
  "caller_wants": "The caller asked to speak with a person about something other than her return, and didn't say what.",
  "summary": "Caller identified by caller ID as Maya Chen, ZIP verified. She returned Dune by Frank Herbert from order 418027 for store credit because she didn't like it. Return ID 1, $27.99 store credit issued, prepaid label emailed, receipt sent by email. She then asked for a person about a new topic she didn't describe. That topic is unresolved.",
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
    "return #1: Dune by Frank Herbert (store_credit, $27.99)"
  ],
  "pending_unconfirmed_change": null
}
```

## End-of-call summary

```json
{
  "call_id": "sim-credit_then_person",
  "duration_s": 25.9,
  "caller_id": "+14155550101",
  "customer": "Maya Chen",
  "identified_via": "caller_id",
  "verification_level": "zip_verified",
  "selected_order": "418027",
  "actions_taken": [
    "return #1: Dune by Frank Herbert (store_credit, $27.99)"
  ],
  "end_reason": "transfer:caller_requested",
  "handoff": {
    "reason": "caller_requested",
    "caller_wants": "The caller asked to speak with a person about something other than her return, and didn't say what.",
    "summary": "Caller identified by caller ID as Maya Chen, ZIP verified. She returned Dune by Frank Herbert from order 418027 for store credit because she didn't like it. Return ID 1, $27.99 store credit issued, prepaid label emailed, receipt sent by email. She then asked for a person about a new topic she didn't describe. That topic is unresolved.",
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
      "return #1: Dune by Frank Herbert (store_credit, $27.99)"
    ],
    "pending_unconfirmed_change": null
  },
  "caller_turns": 5,
  "tool_calls": 6,
  "latency_ms": {
    "p50": 3309,
    "max": 5754
  }
}
```
