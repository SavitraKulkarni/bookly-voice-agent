# Happy path: order status + tracking text

- **Persona:** `happy_path` · James Okafor · caller ID `+13125550142`
- **Shows:** multi-turn, tool use (lookup_order, send_confirmation), caller-ID identification
- **Result:** PASS (9/9 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 1453 ms, max 1901 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "James Okafor", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "419120", "placed_at": "Thursday, November 19th", "items": [{"title": "Project Hail Mary", "…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hi, yeah, I ordered Project Hail Mary a few days ago and I was wondering when it's gonna show up.

**Bookly:** Got it, the order with Project Hail Mary by Andy Weir. It shipped with USPS and should arrive Tuesday, November 24th. Would you like me to text you the tracking number? _(1408 ms)_

**Caller:** Oh perfect, yeah, please text me the tracking number.

> `send_confirmation` `{"kind": "tracking", "channel": "sms", "order_number": "419120"}` → `{"status": "sent", "channel": "sms", "to": "***-***-0142", "mock": true, "note": "Delivery is mocked (written to the outbox)."}`

**Bookly:** I've texted the tracking number to your phone number ending in 0 1 4 2. Is there anything else I can help with? _(1901 ms)_

**Caller:** Great, thanks. That's all I needed.

> `end_call` `{"reason": "resolved", "goodbye": "You're welcome, enjoy Project Hail Mary, and thanks for calling Bookly!"}` → `{"status": "ending", "instruction": "Say a one-sentence goodbye."}`

**Bookly:** You're welcome, enjoy Project Hail Mary, and thanks for calling Bookly! _(1453 ms)_

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
  "duration_s": 27.7,
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
    "p50": 1453,
    "max": 1901
  }
}
```
