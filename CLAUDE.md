# Bookly Voice Agent — Decagon SE take-home

Voice customer-support agent for **Bookly**, a fictional online bookstore. Assignment: `docs/SE-Take-Home.pdf` (read it before changing scope). The user's early whiteboard sketch is `docs/design-sketch.excalidraw` — superseded by this file where they differ (e.g. no vector DB/RAG). Deadline: today.

Deliverables (from the assignment): a GitHub repo with run instructions (this code) and a 3–5 slide pitch deck (the user writes it; code, README and logs must give them the material).

## Thesis — every design choice traces back to this
> A great CX agent knows its boundaries: it resolves what it can with grounded tool calls, asks when it's unsure, and hands off cleanly when it shouldn't decide.

When making a decision, note it briefly (in the README's decisions section or the commit message) so the user can defend it in the deck.

## Hard rules
- **No all-in-one agentic platforms.** Orchestration, tool calling, state and guardrails live in our code. Twilio, AssemblyAI and Cartesia are just APIs.
- **Python + Anthropic SDK, native tool use, manual tool loop.** No agent frameworks (no LangChain/LlamaIndex/etc.), no Tool Runner, no Managed Agents.
- **Depth over breadth.** A working demo beats a fancy one.
- **Secrets:** keys live only in `.env` (user fills it). `.env` is in `.gitignore` before `git init`. Never print, log or echo key values — not in code, logs, commands or chat.
- Don't start a build tier until the previous one works.

## Architecture
```
Caller → Twilio Media Stream (μ-law 8 kHz, WebSocket)
       → AssemblyAI streaming STT
       → Orchestrator (Claude + tools + state + guardrails)   ← text CLI plugs in here too
       → Cartesia TTS (μ-law 8 kHz)
       → Twilio → Caller
```
- **Orchestrator** is transport-agnostic: text CLI, simulations and phone mode all drive the same `Agent.handle_turn()`.
- **Procedures:** one plain-language file per intent in `procedures/` (`order-status.md`, `returns-refunds.md`, `general-faq.md`), loaded into the system prompt. Written so a non-engineer can edit them. No code in them.
- **State:** a structured `CallState` object, separate from the transcript: `verified_customer`, `verification_level` (`none` | `caller_id` | `order_number` | `email` | `zip_verified`), `selected_order`, `pending_action`, plus clarify/escalation counters. Tools read and write it; code (not the model) enforces gates from it.
- **Data:** SQLite — customers, orders, order_items, returns. FAQ in `data/faq.md`, searched by `search_faq` (keyword/section match; no vector DB).
- **Observability:** JSONL log per call — every transcript turn, every tool call (args, result, ms), per-turn latency (STT final → first TTS byte in phone mode; model+tools in text mode), and an end-of-call summary.

## Call flow
1. Greeting, verbatim: "Thanks for calling Bookly. I'm Bookly's AI assistant. How can I help you today?"
2. Route to **order status**, **return/refund**, or **general questions**. Unclear intent → one clarifying question → still unclear → transfer.
3. **Identity scales with risk.**
   - Read-only: caller-ID match is enough.
   - Writes (refund, store credit, cancel, password reset): also need the ZIP code on file.
   - No caller-ID match: ask for order number; email as last resort.

### Order status
- Multiple orders or a multi-book order → ask which one, confirming **title + author**. This is the primary clarifying-question demo.
- Report status from data only.
- Status `processing` → offer to cancel instead of return. Status `lost` → escalate.

### Return / refund
Confirm the book → capture the reason → offer store credit first → accept a refund on the first "no" (never push twice) → read back and confirm before issuing → idempotent write → offer a receipt (`send_confirmation`).

### General
Answer only from the FAQ. Not found → say so and offer a transfer. Password reset → `send_password_reset` (mocked).

## Guardrails
- **Always escalate:** refunds outside policy, lost/damaged orders, angry or repeat callers, unresolved after one clarifying question. Every hand-off carries a reason + structured summary (who, verified how, intent, order, what was tried) so the customer never repeats themselves.
- State policy; never negotiate exceptions.
- Never present partial or missing data as fact.
- Confirm before collecting personal info and before any write.
- Voice style: short responses (1–2 sentences), read numbers digit by digit, confirm book titles back.
- Guardrails that matter are enforced in code (tool preconditions on `CallState`), not only in the prompt. The prompt explains; the code refuses.

## Tools
- `lookup_customer(method: caller_id | email)` — caller ID comes from the carrier (Twilio `From` / CLI `--phone`), never from a number the caller speaks. Code runs the caller-ID lookup automatically at call start.
- `lookup_order(order_number)` — also identifies an unknown caller (read access to that order only).
- `verify_zip(zip)` — matches the account ZIP or the selected order's shipping ZIP. Required for every write. Two failures → no writes, offer transfer.
- `cancel_order(order_number)` — `processing` orders only.
- `start_return(order_number, item, reason, resolution: refund | store_credit)` — records the return. Refund goes to the original payment after the book is received.
- `issue_store_credit(return_id)` — pays store credit immediately for a store-credit return. Idempotent on return_id.
- `search_faq(query)`, `send_password_reset()` (mock, sends to email on file), `send_confirmation(channel)` (SMS/email mocked to the tool log — A2P 10DLC not registered; only to the caller ID or email on file), `transfer_to_human(reason, summary)`, `end_call()`.
- Writes are two-phase in code: first call returns a read-back and stores `pending_action`; only a second call after the caller's next turn executes it. All writes are idempotent.

## Seed data must cover
Multi-order customer; multi-book order; statuses `processing` (offer cancel), `shipped`, `delivered`, `lost` (escalate); one delivered order inside the 30-day return window and one outside; an unknown phone number (not in DB); a repeat caller (`recent_contacts` ≥ 2 → escalate). Dates are seeded relative to today so the 30-day window always holds.

## Build tiers (in order)
- **P0 — text agent.** SQLite + seed, agent core, procedures, tools, text CLI (`--phone` simulates caller ID), simulations script with personas: happy path, multi-book clarifying, return with credit declined, outside window, unknown caller, angry → transfer.
- **P1 — phone mode end to end.** Filler line while tools run ("Let me pull that up"), silence reprompt once then goodbye, AssemblyAI `keyterms_prompt` with catalog titles, end-of-call summary log.
- **P2 — polish.** Stream Claude → Cartesia sentence by sentence, barge-in, real Twilio transfer to the user's cell.
- **Always:** README with run instructions for both modes, assumptions, a decisions log (choice / trade-off / why — feeds the deck), a "Requirements map" (multi-turn / tool use / clarifying question → exact simulation or call that shows each), and a short "How I built this." Simulation transcripts are committed to `docs/transcripts/` so reviewers can read them without API keys. Final step: push to a GitHub repo.

## Model
- Agent: `claude-opus-5-5`; effort from `BOOKLY_EFFORT` (code default `high`; the user's `.env` sets `low`, which is what all measured runs used) (adaptive thinking is always on for this model). Both set in `.env` (`BOOKLY_MODEL`, `BOOKLY_EFFORT`). Per-turn latency is logged so the user can compare models/efforts.
- Opus 5.5 rejects forced `tool_choice`, `budget_tokens` and assistant prefill — steer with the prompt. Message history is append-only.
- Latency levers on by default: `BOOKLY_PREFETCH=1` (live order details in the state note) and `BOOKLY_TERMINAL_SAY=1` (end_call/transfer carry the spoken line).
- Server-side refusal fallback is OFF by default (`BOOKLY_REFUSAL_FALLBACK=0`): a refusal or model error hands off to a human, per the thesis.

## Setup facts
- Bookly Twilio number: +18382322421.
- Twilio account is upgraded (not trial): transfers to any number work.
- ngrok static domain is configured on this machine; the user fills `PUBLIC_HOST` in `.env`.
- `.env.example` lists variable names only: Anthropic key + model, AssemblyAI key, Cartesia key + voice ID, Twilio SID/token/number, transfer number, public host.
- Python: system `python3` is 3.9 (too old for current Anthropic SDK); use Homebrew `python3.13` in a `.venv`.

## Commands (fill in as they exist)
- Text mode: `python -m bookly.cli --phone +1...`
- Simulations: `python -m bookly.simulate`
- Phone mode: `python -m bookly.server` + ngrok
