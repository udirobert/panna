# Judge it in 3 minutes

Panna is a multi-agent match-intelligence broadcast with one rule borrowed
from the Inside the Game winners: **AI tells the story, code keeps the
score.** Every number on screen was recounted from the event ledger by a
deterministic Verifier before it aired.

## The 3-minute path

| Time | Do this | You see |
|---|---|---|
| 0:00 | Open the app, press **GENERATE & KICK OFF** | A seeded match replays at 60×; the pitch board draws events, detections, insights, commentary |
| 0:30 | Click any insight's **✓ verified · why?** chip | The exact recount checks the line passed — stat values, minute refs, score, evidence ids |
| 1:00 | Click **🎛 STUDIO** | The producer console: every line, its verdict, its air status |
| 1:30 | Press **⚠ SEED A BAD CLAIM** | Two fabricated lines are injected — a wrong scoreline and an invented xG figure |
| 1:45 | Watch the HOLD queue | Both land in `held`, rejected by the Verifier, with the failed checks shown. Approve one → it airs; kill the other → it's gone |
| 2:15 | Back on the match, darken **CHALK** in the agent rail | Insights buffer; recover and they flush with `recovered` traces |
| 2:30 | Switch the feed selector to **🎧 Audio description** | A second, deterministic voice describes the action from event positions/outcomes — an accessibility feed that needs no model |
| 2:45 | `GET /status` | Honest component list — what's real in this process, what's staged — plus per-match token cost and translator usage |

## CLI proofs (no UI needed)

```bash
uv run python -m src.cli redteam    # plant 6 classes of false line → catch rate + report
uv run python -m src.cli evaluate   # detection coverage + verification scorecard
uv run python -m src.cli            # the full pipeline, with per-line verdicts
```

Latest red-team run: **6/6 planted false lines caught, 0/43 honest lines
rejected** — see [reports/verifier-redteam.md](../reports/verifier-redteam.md).

## Judging criteria → evidence

| Criterion | Where to look |
|---|---|
| Technological implementation | `src/agents/verifier.py` (deterministic recount gate), `src/models/` (xG, PPDA, momentum, influence, formations), `tests/` (44 tests incl. verifier + producer-gate suites) |
| Agentic design & innovation | Scout → Analyst (MAF tool loop) → Booth → **Gate** → Producer hold. Failure injection + stigmergic recovery. Roles are real code, not prompts |
| Real-world impact | Producer console (approve/kill), audit trail per line, keyless Entra auth, pause-when-empty cost guard, `/status` honesty endpoint |
| UX & presentation | Broadcast replay UI, evidence chips, "why?" panels, producer studio, shareable case file (`/share/{match}`), deterministic `?match=&seed=` URLs |
| Adherence to category | Synthetic seeded matches only — no real PL data. Insights, narratives, recaps, personalized share posters — all explainable |
| Best Use of Foundry | `src/foundry/` — MAF agent for Chalk, GPT-5.4 Booth + Verdict narration, per-call tracing (`/agentic/tracing/{match}`), honest fallback |
| Multi-agent orchestration | `src/agents/` — 5 distinct roles + gate; Director orchestrates, Verifier holds, producer decides |
| Azure cloud native | `azure/panna-aca.bicep` — system-assigned managed identity + `Cognitive Services OpenAI User` role assignment, httpConcurrency scaling, health probes; no stored secrets |
