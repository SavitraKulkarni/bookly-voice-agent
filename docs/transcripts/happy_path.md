# Happy path: order status + tracking text

- **Persona:** `happy_path` · James Okafor · caller ID `+13125550142`
- **Shows:** multi-turn, tool use (lookup_order, send_confirmation), caller-ID identification
- **Result:** PASS (9/9 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 1997 ms, max 2571 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "James Okafor", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "419120", "placed_at": "2026-11-18", "items": [{"title": "Project Hail Mary", "author": "And…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hey, yeah, I ordered Project Hail Mary a few days ago and I'm just wondering when it's gonna get here.

**Bookly:** Your order with Project Hail Mary by Andy Weir shipped by USPS and should arrive Monday, November 23rd. Would you like me to text you the tracking number? _(1997 ms)_

**Caller:** Oh nice, yeah, please text me the tracking number.

> `send_confirmation` `{"kind": "tracking", "channel": "sms", "order_number": "419120"}` → `{"status": "sent", "channel": "sms", "to": "***-***-0142", "mock": true, "note": "Delivery is mocked (written to the outbox)."}`

**Bookly:** I've texted the tracking number to your phone number ending in 0 1 4 2. Can I help with anything else? _(2571 ms)_

**Caller:** Great, thanks. That's all I needed.

> `end_call` `{"reason": "resolved", "goodbye": "Thanks for calling Bookly, James, and enjoy Project Hail Mary!"}` → `{"status": "ending", "instruction": "Say a one-sentence goodbye."}`

**Bookly:** Thanks for calling Bookly, James, and enjoy Project Hail Mary! _(1813 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words, no markdown/URLs | ✅ |
| identified by caller ID at call start | ✅ |
| order 419120 data from the system | ✅ |
| status given from data (shipped) | ✅ |
| tracking texted to caller ID | ✅ |
| no writes, no transfer | ✅ |

## End-of-call summary

```json
{
  "call_id": "sim-happy_path",
  "duration_s": 33.5,
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
    "p50": 1997,
    "max": 2571
  }
}
```
