# Bookly voice support agent

A voice customer-support agent for Bookly, a fictional online bookstore. Built for the Decagon Solutions Engineering take-home ([assignment](docs/SE-Take-Home.pdf)).

> **Thesis:** A great CX agent knows its boundaries: it resolves what it can with grounded tool calls, asks when it's unsure, and hands off cleanly when it shouldn't decide.

**Status:** text mode, simulations (P0) and phone mode (P1) work end to end. Streaming sentence-by-sentence, barge-in and a real transfer (P2) are next.

```
Caller → Twilio media stream (8 kHz μ-law) → AssemblyAI streaming STT
       → orchestrator: Claude (Opus 5.5) + tools + call state + guardrails   ← text CLI and simulations plug in here
       → Cartesia TTS (8 kHz μ-law) → Twilio → caller
```

## Run it (text mode)

```bash
/opt/homebrew/bin/python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env            # then fill in ANTHROPIC_API_KEY
.venv/bin/python -m data.seed   # creates data/bookly.db
.venv/bin/python -m bookly.cli --phone +14155550101 -v
```

- `--phone` simulates caller ID (see [data/seed.py](data/seed.py) for the seeded customers; `+15125550199` is an unknown number).
- Simulations: `.venv/bin/python -m bookly.simulate` (transcripts in [docs/transcripts/](docs/transcripts/)).
- Guardrail tests (no API key needed): `.venv/bin/python -m pytest -q tests`.

## Run it (phone mode)

Needs the voice keys in `.env` (`ASSEMBLYAI_API_KEY`, `CARTESIA_API_KEY`, `CARTESIA_VOICE_ID`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`) and `PUBLIC_HOST` set to your ngrok domain (no `https://`).

```bash
.venv/bin/python -m bookly.voice.server
```

```bash
ngrok http --url=$PUBLIC_HOST 8080
```

Point the Twilio number's Voice webhook at `https://$PUBLIC_HOST/voice` (HTTP POST), then call it. Requests without a valid Twilio signature get a 403.

- **Test without a phone:** with the server running, `.venv/bin/python -m bookly.voice.loopback --phone +13125550142` plays the part of Twilio. It speaks scripted caller lines and prints time to first audio per turn. `--phone +14155550101` runs the clarifying-question script; `--silent` checks the silence reprompt and hang-up.
- **What a call adds on top of the agent:** fixed lines (greeting, "Let me pull that up.", reprompt) are synthesized once at startup and play instantly. A filler line plays as soon as a tool round starts. After 8 s of silence the agent asks "Are you still there?" once, and after another 8 s it says goodbye and hangs up. Catalog titles and authors are sent to AssemblyAI as key terms.
- **Logs:** each call writes `logs/call-<id>.jsonl` with every transcript turn, tool call, and a `voice_turn` timing per turn: speech-to-text delay, agent time, TTS first byte, and time to first audio. The end-of-call summary is printed by the server and logged as `call_end`.

### Measured on the phone path

Time to first audio runs from the end of the caller's speech to the first sound back. Measured on the server's audio clock; the loopback tester's own timing agreed to within ~80 ms.

| Call | Median | Worst | Where the time goes |
|---|---|---|---|
| Real call (unknown caller: capabilities, FAQ, return, bad order number) | 1.78 s | 2.51 s | STT ~0.23 s · agent 1.3–2.4 s · TTS first byte ~0.17 s |
| Loopback, James (status + tracking text) | 1.86 s | 2.15 s | Tool turn: filler at 1.75 s, answer at 3.1 s |
| Loopback, Maya (clarifying question) | 1.84 s | 2.83 s | Worst turn: STT waited 1.3 s after a sentence ending in a book title |

The agent's model time is the largest term. Streaming the first sentence to TTS (P2) is the next lever. Spoken order numbers make STT wait longer (1.4 s after "123456" on the real call); AssemblyAI's `min_latency` mode (`ASSEMBLYAI_MODE`) would shorten that at the risk of cutting off slow speakers.

## Requirements map

| Assignment requirement | Where to see it |
|---|---|
| Multi-turn interaction (collecting info before acting) | [return_credit_declined.md](docs/transcripts/return_credit_declined.md): book → reason → ZIP → credit offer → read-back → confirm → receipt. Also [unknown_caller.md](docs/transcripts/unknown_caller.md): order number → status → ZIP → cancel. |
| Agent takes an action / uses a tool | Same two transcripts (`start_return`, `cancel_order`, `send_confirmation`), [happy_path.md](docs/transcripts/happy_path.md) (texts tracking), every transcript's tool lines. Gates tested offline in [tests/test_tools.py](tests/test_tools.py). |
| Asks a clarifying question instead of answering | [multi_book_clarify.md](docs/transcripts/multi_book_clarify.md): three orders, so it asks which one by title + author before answering. Same on the phone: `bookly.voice.loopback --phone +14155550101`. |
| Knows when to hand off | [angry_transfer.md](docs/transcripts/angry_transfer.md) and [outside_window.md](docs/transcripts/outside_window.md), with the structured handoff packet. |
| Type or speak queries | Text: `bookly.cli`. Voice: call the Twilio number (phone mode above). |

All six simulations are graded by code from the call log, state and database; the latest results are in [docs/transcripts/README.md](docs/transcripts/README.md).

## Assumptions

- **Identity:** the carrier's caller ID is enough to read order info. Anything that changes something also needs the ZIP on file (account or shipping ZIP). A number the caller says out loud is never treated as caller ID. No caller-ID match: order number (read access to that order only), then email as a last resort.
- **Returns:** 30 days from delivery, one return per book. Store credit is added immediately; a refund goes to the original payment 5–7 business days after the book arrives. Processing orders are cancelled rather than returned.
- **Escalation:** angry callers, repeat callers (2+ support contacts in 14 days), lost or damaged orders and out-of-policy requests go to a person with a structured summary.
- **Mocks:** SMS and email are written to an `outbox` table and the tool log (A2P 10DLC isn't registered, so no real texts). The password reset is mocked. Data is seeded relative to today's date.
- **Transfer (P1):** the agent says the handoff line, logs the handoff packet, and ends the call. The real Twilio transfer is P2.

## How I built this

Python with the Anthropic SDK and a hand-written tool loop; no agent framework. Twilio, AssemblyAI and Cartesia are called directly over their WebSocket APIs. I wrote it with Claude Code as a pair: I set the thesis, architecture, call flow and guardrails up front (see [CLAUDE.md](CLAUDE.md)) and reviewed each tier before moving on. Claude wrote most of the code, the procedures and the simulations, and checked API details against each vendor's current docs. Quality was checked by code-graded simulations (6 personas, re-run after every behavior change) and guardrail tests that run without the model. Latency was improved by measuring first (A/B in one run, configs interleaved), not guessing.

## Decisions log

Each entry: what I chose, what it costs, and why it was worth it.

### 1. Guardrails are enforced in code, not just the prompt
- **Choice:** The prompt explains the rules; the tools refuse when the rules aren't met. Each tool checks the structured call state ([bookly/state.py](bookly/state.py)) before acting ([bookly/tools.py](bookly/tools.py)):
  - every write needs a verified ZIP, and two wrong ZIPs lock changes for the rest of the call;
  - every write is two-phase: the first call only returns a read-back, and the change runs only on a second call after the caller has replied, with the same details;
  - writes are idempotent (one return per book, one credit per return, deduplicated messages);
  - a return outside the 30-day window comes back as a policy error that tells the model to state the policy and offer a transfer;
  - a caller identified by order number can see only that order, and another customer's order looks "not found";
  - texts go only to the number the caller is calling from.
- **Trade-off:** More code than a prompt-only agent, and some rigidity: a caller can't, say, verify by a method the code doesn't know about.
- **Why:** A prompt is a request; a model can be talked out of it, especially by a persistent caller. For anything that moves money or touches an account, the boundary has to hold even when the model gets it wrong. It also makes the guardrails testable without the model: [tests/test_tools.py](tests/test_tools.py) checks every gate offline.

### 2. Refusals and errors hand off to a human, no silent retry
- **Choice:** If the model errors, refuses, or loops on tools, the agent says one sentence and transfers to a person with whatever context it has. Anthropic's server-side refusal fallback (retrying on another model) is available but **off by default** (`BOOKLY_REFUSAL_FALLBACK=0`).
- **Trade-off:** Some calls a fallback model could have finished go to a person instead.
- **Why:** That's the thesis: when the agent can't stand behind an answer, it hands off cleanly rather than improvising with a different model.

### 3. Caller ID lookup runs in code at call start
- **Choice:** The caller-ID account lookup is done by code before the model sees the first turn, using the carrier's number. A number the caller says out loud is never treated as caller ID.
- **Trade-off:** One less thing the model decides.
- **Why:** Identity shouldn't depend on what the model believes; it's deterministic, faster, and can't be socially engineered.

### 4. Procedures are plain-language files
- **Choice:** One Markdown file per intent in [procedures/](procedures/), loaded verbatim into the system prompt.
- **Trade-off:** Less structure than a state machine; behaviour within a procedure is the model's judgment.
- **Why:** A CX team can read and edit how the agent behaves without an engineer, and the code still enforces the parts that matter (decision 1).

### 5. Simulations are graded by code, not by a model
- **Choice:** A model plays the caller, but pass/fail comes from the call log, call state and database: did the right tool run, was the ZIP verified first, was a return row written, was the handoff reason right.
- **Trade-off:** Checks are specific to each persona and need writing by hand.
- **Why:** "Did the agent do the right thing?" is answered by what it did, not by another model's opinion of the conversation.

### 6. Latency: cut round trips, not tokens
- **Finding:** Round trips were the bottleneck. Each model call costs about 0.85 s before it writes anything, plus ~7 ms per output token, and replies are short (median 67 tokens, thinking included). Tools take ~0 ms. In the baseline, 55 of 66 turns made two calls (run a tool, then speak) at ~2.7 s; one-call turns took ~1 s. So lower effort or a faster-output mode moves little; fewer calls moves a lot.
- **Choice:** Two changes, on by default (`BOOKLY_PREFETCH`, `BOOKLY_TERMINAL_SAY`):
  - *Prefetch:* once caller ID (or email) identifies the account, code re-reads the live order details every turn and puts them in the call-state note, so status and return-eligibility turns skip the `lookup_order` round trip. Still from the system of record, just fetched by code.
  - *Terminal tools carry their line:* `transfer_to_human` and `end_call` include the sentence to speak, so ending a call needs no follow-up model call. The angry caller hears the handoff sooner.
- **Measured** (one run, 54 simulated calls, configs interleaved, 3 repeats each, Opus 5.5 at effort `low` as set in `.env`):

  | Setup | Calls fully passing | Median turn | Slowest 1 in 10 | Model calls / turn | Agent cost / conversation* |
  |---|---|---|---|---|---|
  | Baseline | 18/18 | 2.7 s | 4.0 s | 1.89 | $0.043 |
  | **Prefetch + terminal line** | 17/18† | **2.3 s** | **3.7 s** | **1.45** | $0.047 |
  | Same + effort `medium` | 18/18 | 2.4 s | 4.0 s | 1.45 | $0.041 |

  \* Agent model calls only (not the simulated caller), from logged token counts at Opus 5.5 list prices ($4 in / $20 out / $0.20 cache read per million tokens). Conversations averaged ~3.7 caller turns. The final verification run of the six personas cost $0.032 per conversation.
  † The one miss was an over-strict check (the agent named the right book, "Klara and the Sun", but the check wanted the other title). The check was widened and the final run passed 6/6.
- **Trade-off:** Prefetch makes each call ~0.25 s slower (bigger state note, more to read) and costs ~$0.004 more per conversation; the saved round trips more than pay it back. The model also sees statuses before it asks "which order?". The clarifying-question simulation checks it still asks first (3/3 in the A/B, plus the final run).
- **Not yet measured:** each change alone, and effort `high`. The biggest remaining lever for callers is in phone mode: a filler line during tool calls and streaming the first sentence to TTS, measured as time to first audio.
