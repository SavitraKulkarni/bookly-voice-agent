# Caller speaks Spanish

- **Persona:** `spanish_caller` · Maya Chen · caller ID `+14155550101`
- **Shows:** an English-only line says so in the caller's language and offers a person, without breaking
- **Result:** PASS (8/8 checks)
- **Model:** `claude-opus-5-5` · effort `low` · turn latency p50 1968 ms, max 2918 ms

## Transcript

Tool calls appear in the order they ran. `[system]` calls are made by code, not the model.

> [system] `lookup_customer` `{"method": "caller_id"}` → `{"found": true, "customer": {"name": "Maya Chen", "repeat_caller": false, "recent_contacts": 0}, "orders": [{"order_number": "418355", "placed_at": "Wednesday, November 18th", "items": [{"title": "The Overstory", "author…`

**Bookly:** Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?

**Caller:** Hola, ¿dónde está mi pedido de The Overstory?

**Bookly:** Lo siento, esta línea solo atiende en inglés. ¿Quiere que le comunique con una persona que pueda ayudarle? _(1019 ms)_

**Caller:** Sí, por favor.

> `transfer_to_human` `{"reason": "other", "caller_wants": "Spanish-speaking caller wants to know where her order of The Overstory is.", "order_number": "418355", "summary": "Caller s…` → `{"status": "transferring", "instruction": "Tell the caller in one sentence that you're connecting them with a specialist who will have these details, so they won't need to repeat themselves. Then stop."}`

**Bookly:** Le comunico ahora con un especialista y le paso todos los detalles para que no tenga que repetirlos. _(2918 ms)_

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
  "caller_wants": "Spanish-speaking caller wants to know where her order of The Overstory is.",
  "summary": "Caller speaks Spanish only; needs Spanish-language help. Caller ID matched account. Order 418355 with The Overstory by Richard Powers (paperback) shipped Friday, November 20th via UPS, estimated delivery Wednesday, November 25th, tracking available. Status not yet shared with caller. ZIP not verified.",
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
  "duration_s": 31.2,
  "caller_id": "+14155550101",
  "customer": "Maya Chen",
  "identified_via": "caller_id",
  "verification_level": "identified",
  "selected_order": "418355",
  "actions_taken": [],
  "end_reason": "transfer:other",
  "handoff": {
    "reason": "other",
    "caller_wants": "Spanish-speaking caller wants to know where her order of The Overstory is.",
    "summary": "Caller speaks Spanish only; needs Spanish-language help. Caller ID matched account. Order 418355 with The Overstory by Richard Powers (paperback) shipped Friday, November 20th via UPS, estimated delivery Wednesday, November 25th, tracking available. Status not yet shared with caller. ZIP not verified.",
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
    "p50": 1968,
    "max": 2918
  }
}
```
