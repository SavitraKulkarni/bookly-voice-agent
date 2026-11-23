# Password reset

- **Persona:** `password_reset` · James Okafor · caller ID `+13125550142`
- **Shows:** general-question path with a write: ZIP step-up, read-back, mocked email
- **Result:** PASS (6/6 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 2537 ms, max 3022 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "James Okafor", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "419120", "placed_at": "Thursday, November 19th", "items": [{"title": "Project Hail Mary", "…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hey, yeah, I'm locked out of my Bookly account. Can you help me reset my password?

**Bookly:** I can help with that. To make changes, I need to verify the ZIP code on the account. What's your ZIP? _(1513 ms)_

**Caller:** Sure, it's 60614.

> `verify_zip` `{"zip": "60614"}` → `{"verified": true}`

> `send_password_reset` `{}` → `{"status": "needs_confirmation", "read_back": "Email a password reset link to the address on file (j***@example.com).", "instruction": "Read this back to the caller and ask for a clear yes. Only after they agree, call th…`

**Bookly:** Thanks, you're verified. I'll email a password reset link to the address on file. Shall I go ahead? _(3007 ms)_

**Caller:** Yes, please go ahead.

> `send_password_reset` `{"confirmed": true}` → `{"status": "sent", "to": "j***@example.com", "expires_in_minutes": 30}`

**Bookly:** I've sent the reset link to the email address on your account. It expires in 30 minutes, so try to use it soon. Can I help with anything else? _(3022 ms)_

**Caller:** Nope, that's it. Thanks, bye!

> `end_call` `{"reason": "resolved", "goodbye": "You're welcome, thanks for calling Bookly, and have a great day!"}` → `{"status": "ending", "instruction": "Say a one-sentence goodbye."}`

**Bookly:** You're welcome, thanks for calling Bookly, and have a great day! _(2068 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words (book titles/authors not counted), no markdown/URLs | ✅ |
| ZIP verified first | ✅ |
| reset sent once | ✅ |

## End-of-call summary

```json
{
  "call_id": "sim-password_reset",
  "duration_s": 45.9,
  "caller_id": "+13125550142",
  "customer": "James Okafor",
  "identified_via": "caller_id",
  "verification_level": "zip_verified",
  "selected_order": null,
  "actions_taken": [
    "password reset email sent"
  ],
  "end_reason": "end:resolved",
  "handoff": null,
  "caller_turns": 4,
  "tool_calls": 5,
  "latency_ms": {
    "p50": 2537,
    "max": 3022
  }
}
```
