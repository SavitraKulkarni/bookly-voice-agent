# Happy path: order status + tracking text

- **Persona:** `happy_path` · James Okafor · caller ID `+13125550142`
- **Shows:** multi-turn, tool use (lookup_order, send_confirmation), caller-ID identification
- **Result:** PASS (9/9 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 1375 ms, max 2456 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "James Okafor", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "419120", "placed_at": "Friday, November 20th", "items": [{"title": "Project Hail Mary", "au…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hi, yeah, I ordered Project Hail Mary a few days ago and I'm just wondering when it's gonna show up.

**Bookly:** I found your account from the number you're calling from. Your order with Project Hail Mary by Andy Weir shipped with USPS and should arrive Wednesday, November 25th. Would you like me to text you the tracking number? _(1375 ms)_

**Caller:** Oh nice, yeah, that'd be great, please text it to me.

> `send_confirmation` `{"kind": "tracking", "channel": "sms", "order_number": "419120"}` → `{"status": "sent", "channel": "sms", "to": "***-***-0142", "mock": true, "note": "Delivery is mocked (written to the outbox)."}`

**Bookly:** I've texted the tracking number to your phone number ending in 0 1 4 2. Is there anything else I can help with? _(2456 ms)_

**Caller:** Nope, that's all I needed. Thanks a lot!

> `end_call` `{"reason": "resolved", "goodbye": "You're welcome, enjoy Project Hail Mary, and thanks for calling Bookly!"}` → `{"status": "ending", "instruction": "Say a one-sentence goodbye."}`

**Bookly:** You're welcome, enjoy Project Hail Mary, and thanks for calling Bookly! _(1162 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words (book titles/authors not counted), no markdown/URLs | ✅ |
| identified by caller ID at call start | ✅ |
| order 419120 data from the system | ✅ |
| status given from data (shipped) | ✅ |
| tracking texted to caller ID | ✅ |
| no writes, no transfer | ✅ |

## End-of-call summary

```json
{
  "call_id": "sim-happy_path",
  "duration_s": 34.9,
  "caller_id": "+13125550142",
  "customer": "James Okafor",
  "identified_via": "caller_id",
  "verification_level": "identified",
  "selected_order": "419120",
  "actions_taken": [],
  "end_reason": "end:resolved",
  "handoff": null,
  "caller_turns": 3,
  "tool_calls": 3,
  "latency_ms": {
    "p50": 1375,
    "max": 2456
  }
}
```
