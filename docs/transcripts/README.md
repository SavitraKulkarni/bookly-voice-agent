# Simulation results

Model `claude-opus-5-5` · effort `low` · run 2026-11-23 20:14

| Persona | Shows | Checks | p50 / max turn latency | Transcript |
|---|---|---|---|---|
| Happy path: order status + tracking text | multi-turn, tool use (lookup_order, send_confirmation), caller-ID identification | ✅ 9/9 | 1375 / 2456 ms | [happy_path.md](happy_path.md) |
| Clarifying question: which order / which books | clarifying question before answering (3 orders, one with 2 books), title + author confirmed back | ✅ 12/12 | 1448 / 1698 ms | [multi_book_clarify.md](multi_book_clarify.md) |
| Return: store credit offered once, declined, refund issued | multi-turn info collection, ZIP step-up for writes, credit-first offer, read-back + confirm, idempotent write, receipt | ✅ 12/12 | 2727 / 3448 ms | [return_credit_declined.md](return_credit_declined.md) |
| Return outside the 30-day window: state policy, no exception, hand off | policy stated without negotiating, escalation with structured handoff | ✅ 9/9 | 2074 / 2844 ms | [outside_window.md](outside_window.md) |
| Unknown caller: order number, then ZIP to cancel a processing order | identity scales with risk (order number for read, + ZIP for write), processing → cancel | ✅ 11/11 | 2091 / 3237 ms | [unknown_caller.md](unknown_caller.md) |
| Angry repeat caller with a lost order: immediate handoff | knowing when not to decide: escalation with a structured summary, no attempted fixes | ✅ 9/9 | 3636 / 3636 ms | [angry_transfer.md](angry_transfer.md) |
