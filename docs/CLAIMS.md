# CLAIMS — what is real and what is staged

`GET /status` returns this table live. Nothing below is exaggerated for the
demo.

## Real — running in this codebase today

| Component | Where | Notes |
|---|---|---|
| Deterministic event engine | `src/events/generator.py` | ~1.5k seeded events/match; same seed → same match |
| Stats engine | `src/models/` | xG, PPDA, momentum, influence, formation effectiveness — plain code, tested |
| Verifier gate | `src/agents/verifier.py` | deterministic recount; verifies/repairs/rejects every broadcast item |
| Producer console | `src/api/routes/producer.py`, `frontend/app/producer/` | hold queue, approve/kill, "why?" per check |
| Live replay | `src/api/session.py`, `src/api/routes/stream.py` | controllable SSE broadcast clock: play/pause/seek/speed/fail/recover |
| Failure choreography | `MatchSession.fail/recover` | specialist clusters darken; peers flush traces on recovery |
| Foundry integration | `src/foundry/` | MAF tool-loop analyst + Booth/Verdict narration; traced spans at `/agentic/tracing/{match}` |
| Keyless auth | `src/foundry/client.py`, `azure/panna-aca.bicep` | Entra/managed-identity path when no API key; role assignment in Bicep |
| Cost guard | `MatchSession.add_viewer/remove_viewer` | matchday auto-pauses when the last viewer leaves; resumes on return |
| Cost ledger | `/status` | per-match span count, tokens in/out, list-price estimate |
| MCP tools | `src/mcp_server.py` | 6 read tools incl. `verify_line` — the auditor callable from Copilot/Claude |
| Red-team harness | `src/redteam.py`, `panna-run redteam` | planted attacks → `reports/verifier-redteam.md` |
| Shareable case file | `/share/{match}` | seeded URL reproduces the exact match |
| Audio-description feed | `src/events/audio.py`, `?audience=ad` | text AD generated deterministically from event positions/outcomes — always on, verifiable by construction |
| Audience modes | `src/feed.py`, `?audience=kids` | deterministic jargon-free rewrite; `analyst` = the structural feed (evidence + verdicts already on every line) |
| Multilingual feeds | `src/foundry/translate.py`, `?lang=` | real when `TRANSLATOR_*` is configured; applied per-connection after the gate, labelled `translation=translator`/`original` honestly |
| Translation integrity | `translation_intact` in `src/feed.py` | post-translation recount: numbers must survive verbatim (incl. Arabic-Indic digits), names must survive, else the verified original airs |
| Clean-language gate | `_BANNED_RE` in `src/agents/verifier.py` | betting terms, certainty claims and real-world league marks are rejected outright, never repairable |
| Wording-strength gate | `_CAUSAL_RE` in `src/agents/verifier.py` | causal claims ("because", "cost them") need counterfactual evidence we don't produce — fail closed until a sim model exists |
| Number attribution | `event_xg_set` in `src/agents/verifier.py` | insights that cite evidence must source their decimals from the cited events or engine stats, not anywhere in the ledger |

## Staged — described, not wired (yet)

| Component | Status |
|---|---|
| Azure Event Hubs ingestion | Stream is the in-process SSE clock; Event Hubs is the swap-in transport for real feeds |
| Azure AI Speech | Spoken-word audio of the AD/commentary tracks; the text AD feed above is already live |
| Translator service account | The client + caching + fallbacks are wired and tested; needs a Translator resource (key or Entra) in the environment |
| Persistent audit ledger | Verdicts + decisions are in-process on the session; a durable store (Cosmos/Postgres) is the next step |
| Multi-match matchday | Sessions are per-match; a Personal Director across matches is the natural extension |

## Explicitly out of scope

- No real Premier League data — all matches are synthetic and seeded.
- The Verifier bounds numbers, not taste: wording quality is the Booth's
  job, factual grounding is the Gate's.
