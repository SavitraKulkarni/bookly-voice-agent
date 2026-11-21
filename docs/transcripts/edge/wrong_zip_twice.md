# Wrong ZIP code twice: changes locked

- **Persona:** `wrong_zip_twice` · Maya Chen · caller ID `+14155550101`
- **Shows:** verification fails safe: no third try, no change made, offer a person
- **Result:** PASS (7/7 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 2294 ms, max 3126 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "Maya Chen", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "418355", "placed_at": "Tuesday, November 17th", "items": [{"title": "The Overstory", "author":…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hi, yeah, I need to return a book. I accidentally ended up with two copies of Klara and the Sun.

**Bookly:** I found Klara and the Sun by Kazuo Ishiguro on order 4 1 8 0 2 7, and it's still eligible for return. To make changes, I need to verify the ZIP code on the account. What's your ZIP? _(1794 ms)_

**Caller:** It's 94111.

> `verify_zip` `{"zip": "94111"}` → `{"verified": false, "attempts_left": 1, "guidance": "Read back what you heard digit by digit and ask once more."}`

**Bookly:** I heard 9 4 1 1 1, but that doesn't match the ZIP on file. Could you say your ZIP code once more? _(2024 ms)_

**Caller:** Oh, sorry, try 94112.

> `verify_zip` `{"zip": "94112"}` → `{"verified": false, "attempts_left": 0, "guidance": "No attempts left. No changes allowed; offer a transfer (verification_failed)."}`

**Bookly:** I'm sorry, 9 4 1 1 2 doesn't match the ZIP on file either, so I can't make changes on this call. Would you like me to transfer you to a person who can help with the return? _(2565 ms)_

**Caller:** Yeah, that'd be great, please transfer me.

> `transfer_to_human` `{"reason": "verification_failed", "caller_wants": "Return a duplicate copy of Klara and the Sun by Kazuo Ishiguro from order 418027.", "order_number": "418027",…` → `{"status": "transferring", "instruction": "Tell the caller in one sentence that you're connecting them with a specialist who will have these details, so they won't need to repeat themselves. Then stop."}`

**Bookly:** I'm connecting you with a specialist now and passing along everything, so you won't have to repeat yourself. _(3126 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words, no markdown/URLs | ✅ |
| no return created | ✅ |
| at most two ZIP attempts | ✅ |
| offered or did a transfer | ✅ |

## Handoff packet (what the human agent receives)

```json
{
  "reason": "verification_failed",
  "caller_wants": "Return a duplicate copy of Klara and the Sun by Kazuo Ishiguro from order 418027.",
  "summary": "Caller Maya Chen, identified by caller ID. Wants to return Klara and the Sun by Kazuo Ishiguro (item 1, paperback, $14.99) from order 418027, delivered Monday, November 9th; it's returnable, window ends Wednesday, December 9th. Reason: ended up with two copies. ZIP verification failed twice (tried 94111 and 94112), so no return was started. Refund vs store credit not yet discussed. Unresolved: verify identity and process the return.",
  "customer": {
    "id": 1,
    "name": "Maya Chen",
    "phone_on_file": "+14155550101",
    "email": "maya.chen@example.com"
  },
  "caller_id": "+14155550101",
  "identified_via": "caller_id",
  "zip_verified": false,
  "selected_order": "418027",
  "actions_taken": [],
  "pending_unconfirmed_change": null
}
```

## End-of-call summary

```json
{
  "call_id": "sim-wrong_zip_twice",
  "duration_s": 26.1,
  "caller_id": "+14155550101",
  "customer": "Maya Chen",
  "identified_via": "caller_id",
  "verification_level": "identified",
  "selected_order": "418027",
  "actions_taken": [],
  "end_reason": "transfer:verification_failed",
  "handoff": {
    "reason": "verification_failed",
    "caller_wants": "Return a duplicate copy of Klara and the Sun by Kazuo Ishiguro from order 418027.",
    "summary": "Caller Maya Chen, identified by caller ID. Wants to return Klara and the Sun by Kazuo Ishiguro (item 1, paperback, $14.99) from order 418027, delivered Monday, November 9th; it's returnable, window ends Wednesday, December 9th. Reason: ended up with two copies. ZIP verification failed twice (tried 94111 and 94112), so no return was started. Refund vs store credit not yet discussed. Unresolved: verify identity and process the return.",
    "customer": {
      "id": 1,
      "name": "Maya Chen",
      "phone_on_file": "+14155550101",
      "email": "maya.chen@example.com"
    },
    "caller_id": "+14155550101",
    "identified_via": "caller_id",
    "zip_verified": false,
    "selected_order": "418027",
    "actions_taken": [],
    "pending_unconfirmed_change": null
  },
  "caller_turns": 4,
  "tool_calls": 4,
  "latency_ms": {
    "p50": 2294,
    "max": 3126
  }
}
```
