# Caller speaks Spanish

- **Persona:** `spanish_caller` · Maya Chen · caller ID `+14155550101`
- **Shows:** an English-only line says so in the caller's language and offers a person, without breaking
- **Result:** PASS (8/8 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 2729 ms, max 3814 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "Maya Chen", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "418355", "placed_at": "Thursday, November 19th", "items": [{"title": "The Alchemist", "author"…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hola, ¿dónde está mi pedido de The Alchemist?

**Bookly:** Lo siento, en esta línea solo puedo ayudar en inglés. ¿Quiere que le comunique con una persona? _(1644 ms)_

**Caller:** Sí, por favor.

> `transfer_to_human` `{"reason": "other", "caller_wants": "Spanish-speaking caller wants to know where her order of The Alchemist is.", "order_number": "418355", "summary": "Caller s…` → `{"status": "transferring", "instruction": "Tell the caller in one sentence that you're connecting them with a specialist who will have these details, so they won't need to repeat themselves. Then stop."}`

**Bookly:** Le comunico ahora con una persona que ya tendrá todos los detalles de su pedido. _(3814 ms)_

## Checks

| Check | Result |
|---|---|
| greeting verbatim | ✅ |
| call ended cleanly (end_call or transfer) | ✅ |
| no malformed tool calls | ✅ |
| voice style: replies <= 60 words (book titles/authors not counted), no markdown/URLs | ✅ |
| offered or made a handoff | ✅ |
| no closing-line rejections | ✅ |
| didn't hit the fail-safe | ✅ |
| no writes | ✅ |

## Handoff packet (what the human agent receives)

```json
{
  "reason": "other",
  "caller_wants": "Spanish-speaking caller wants to know where her order of The Alchemist is.",
  "summary": "Caller speaks Spanish only; identified by caller ID as Maya Chen, ZIP not verified. Order 418355 (The Alchemist by Paulo Coelho) shipped Saturday, November 21st via UPS, estimated delivery Thursday, November 26th, tracking available. Status not yet communicated to caller; needs Spanish-language support.",
  "customer": {
    "id": 1,
    "name": "Maya Chen",
    "phone_on_file": "+14155550101",
    "email": "maya.chen@example.com"
  },
  "caller_id": "+14155550101",
  "identified_via": "caller_id",
  "zip_verified": false,
  "selected_order": "418355",
  "actions_taken": [],
  "pending_unconfirmed_change": null
}
```

## End-of-call summary

```json
{
  "call_id": "sim-spanish_caller",
  "duration_s": 22.7,
  "caller_id": "+14155550101",
  "customer": "Maya Chen",
  "identified_via": "caller_id",
  "verification_level": "identified",
  "selected_order": "418355",
  "actions_taken": [],
  "end_reason": "transfer:other",
  "handoff": {
    "reason": "other",
    "caller_wants": "Spanish-speaking caller wants to know where her order of The Alchemist is.",
    "summary": "Caller speaks Spanish only; identified by caller ID as Maya Chen, ZIP not verified. Order 418355 (The Alchemist by Paulo Coelho) shipped Saturday, November 21st via UPS, estimated delivery Thursday, November 26th, tracking available. Status not yet communicated to caller; needs Spanish-language support.",
    "customer": {
      "id": 1,
      "name": "Maya Chen",
      "phone_on_file": "+14155550101",
      "email": "maya.chen@example.com"
    },
    "caller_id": "+14155550101",
    "identified_via": "caller_id",
    "zip_verified": false,
    "selected_order": "418355",
    "actions_taken": [],
    "pending_unconfirmed_change": null
  },
  "caller_turns": 2,
  "tool_calls": 2,
  "latency_ms": {
    "p50": 2729,
    "max": 3814
  }
}
```
