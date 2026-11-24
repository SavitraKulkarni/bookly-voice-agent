# Password reset

- **Persona:** `password_reset` · James Okafor · caller ID `+13125550142`
- **Shows:** general-question path with a write: ZIP step-up, read-back, mocked email
- **Result:** PASS (6/6 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 2068 ms, max 2978 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "James Okafor", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "419120", "placed_at": "Friday, November 20th", "items": [{"title": "Project Hail Mary", "au…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hi, yeah, I'm locked out of my Bookly account and I need to reset my password.

**Bookly:** I found your account from the number you're calling from. To make changes, I need to verify the ZIP code on the account. What's your ZIP? _(1658 ms)_

**Caller:** It's 60614.

> `verify_zip` `{"zip": "60614"}` → `{"verified": true}`

> `send_password_reset` `{}` → `{"status": "needs_confirmation", "read_back": "Email a password reset link to the address on file (j***@example.com).", "instruction": "Read this back to the caller and ask for a clear yes. Only after they agree, call th…`

**Bookly:** Thanks, your ZIP is verified. I'll email a password reset link to the address we have on file. Shall I go ahead? _(2479 ms)_

**Caller:** Yes, please go ahead.

> `send_password_reset` `{"confirmed": true}` → `{"status": "sent", "to": "j***@example.com", "expires_in_minutes": 30}`

> `search_faq` `{"query": "password reset link expiration"}` → `{"found": true, "results": [{"topic": "Password reset", "answer": "We can email a password reset link to the address on your account. The link expires in 30 minutes. For security, support can't change the email address o…`

**Bookly:** I've sent the reset link to your email on file. It expires in 30 minutes. Is there anything else I can help with? _(2978 ms)_

**Caller:** No, that's it. Thanks, bye!

> `end_call` `{"reason": "resolved", "goodbye": "You're welcome, thanks for calling Bookly, and have a great day!"}` → `{"status": "ending", "instruction": "Say a one-sentence goodbye."}`

**Bookly:** You're welcome, thanks for calling Bookly, and have a great day! _(1271 ms)_

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
  "duration_s": 43.4,
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
  "tool_calls": 6,
  "latency_ms": {
    "p50": 2068,
    "max": 2978
  }
}
```
