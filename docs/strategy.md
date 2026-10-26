# Panna — Build strategy (revised 2026-10-25)

> Supersedes the original generic plan. See `docs/critique.md` for the research-backed rationale.
> **Presentation layer supersession:** `docs/design-vision.md` (v2, "The Pitch Is the Blackboard")
> governs the frontend, agent presentation identity, failure-recovery visuals, and the demo
> film ("The Verdict"). This doc stays authoritative for backend/stack/schedule.
> **Deadline: Oct 27, 2026 11:59 pm PT. Today is Oct 25 — ~2 days.**

## Goal

Win multiple prize categories simultaneously by visibly using 2026 Microsoft hero tech:
a Microsoft Agent Framework reasoning loop with tool-calling agents, Foundry GPT-5.4
narration and verdicts, span tracing for every agent call, ACA deployment, plus a
polished Next.js frontend. Synthetic football data only. Every insight carries
evidence citations.

## Tech stack (as built 2026-10-26 — see README for live/staged/cut)

- **Orchestration:** the Director runs a shared-state blackboard (stigmergy):
  staggered reveals on the match clock, per-agent health, failure injection with
  peer recovery. Multi-agent by design, not message-passing.
- **Reasoning:** Microsoft Agent Framework (MAF) — Chalk is an `agent_framework.Agent`
  on Azure OpenAI with a six-function toolkit (xG, PPDA, formation, influence,
  momentum, event windows). The model must cite real event ids; output is
  validated against the ledger before it reaches the board.
- **Narration:** Foundry GPT-5.4 (Booth) in the live Director path; Verdict
  recap agent at full time. Both traced, both with deterministic fallback.
- **Governance:** per-call span tracing (agent, model, tokens, status) at
  `/agentic/tracing`; `/health` reports Foundry availability.
- **Compute:** Azure Container Apps (FastAPI API, httpConcurrency scaling,
  health probe, `@secure()` secret) via `azure/deploy.sh`.
- **Frontend:** Next.js — the pitch *is* the interface (design-vision v2): no card
  grid; chalk telestration, boids swarm, pitch-control glow, Ceefax-style ticker,
  score bug, lens switching, SSE replay with rewind/freeze/failure injection.
- **Data:** synthetic StatsBomb-like event schema, seeded deterministic match (~90 min, ~1500 events), real xG/PPDA/formation models.

## The 4-agent pipeline (plus Recap)

Backend modules keep these names. Their **presentation identity** (per
`docs/design-vision.md` §1) is: **Numbers see it, Chalk proves it, Booth says it** —
and the Pitch itself is the fourth actor (a blackboard, not a boss).

| Agent (backend) | Presentation identity | Role | Output |
|---|---|---|---|
| **Scout** | **Numbers** — the swarm | Watches synthetic stream; flags key moments (shots, tackles, possession shifts, formation changes, set pieces) | Structured markers: `{event_id, minute, type, importance, evidence:[event_ids]}` |
| **Analyst** | **Chalk** — the specialists | Computes tactical insights: xG per shot (distance/angle/body part), PPDA pressing intensity, formation effectiveness, player influence (xT/network), momentum (rolling xG) | Insights: `{id, type, claim, value, confidence, evidence:[event_ids]}` |
| **Commentator** | **Booth** | Timed broadcast NL from Scout+Analyst, cites insights, professional tone | Commentary entries with minute/second timing |
| **Director** | **the Pitch** (coordination as a place) | Shared-state blackboard orchestration, prioritization, staggered reveals, failure recovery (deterministic fallback), agent health | Curated broadcast feed |
| **Recap** (Day2) | recap = the annotated board, printed | Post-match summary from all above | Recap text + top insights |

## Explainability contract

Every insight = `{id, type, claim, value, confidence, evidence: [event_ids], agent, timestamp}`.
UI renders evidence as an **Evidence Spotlight** (per design-vision §2): chalk/telestration
marks on the pitch with gold attribution lines back to the claim — no tooltip cards.
ASSERT evals enforce "every claim cites ≥1 event" and "no fabricated events".

## Failure recovery (explicitly judged)

Director wraps each agent call in try/except with timeout + exponential backoff retry + degraded-mode fallback:
- Analyst down → Scout still surfaces raw key moments; Commentator falls back to template.
- Commentator down → insights still published.
- Emit agent-health events to frontend (green/amber/red per agent).

**Presentation** (design-vision §1): recovery is shown as *emergence* — a specialist
cluster goes dark, its half-drawn chalk stays on the board (stigmergy), peer particles
converge on the orphaned traces and finish the annotation. No amber status cards in
the film; the scriptable failure-injection endpoint drives the rehearsed demo beat.

## Compressed 48h plan

### Day 1 (Oct 25) — core pipeline + frontend ✅ (scaffolded)
- Morning: Synthetic data generator (StatsBomb-like schema, seeded match) + xG/PPDA/formation models. Commit.
- Midday: Scout + Analyst agents (Chalk on MAF when Foundry is live), evidence citations. Local run.
- Afternoon: Commentator agent (timed, broadcast tone) + Director (shared-state blackboard, failure recovery).
- Evening: Next.js frontend v1 (card grid, shipped in scaffold commit). **Superseded by Day 2 vision build.**

### Day 2 (Oct 26) — the vision build + cloud + polish + submit

Frontend work follows `docs/design-vision.md` §7 — **build the shots, not the screens**
(every item maps to a beat in "The Verdict" demo film):

1. SSE stream + replay clock + rewind/freeze/failure-injection controls
2. Pitch SVG + chalk telestration system + Evidence Spotlight
3. Boids swarm canvas (~40–80 particles, flocking + quorum hardening)
4. Pitch-control glow + momentum/xG SVG (BBC-style)
5. Ticker band + score bug + lens switching (tactical/attack/story)
6. Specialist failure/recovery choreography, rehearsed
7. Recap = annotated-board print layout
8. Seed regeneration on air + invitation screen
9. Sound pass + title cards naming rubric criteria

Cloud work, morning in parallel where possible: deploy API to ACA
(`azure/deploy.sh`); Booth staged as a Foundry hosted agent definition
(`foundry-config/booth-agent.yaml`); span tracing for every agent call
(Shipped: MAF loop, tracing, share/viral loop, Verdict recap). Event Hubs
ingestion cut (SSE from API). Foundry IQ cut. Midday: lens personalization
(Memory; cut → toggle). Demo video afternoon (<2 min, "The Verdict" script)
+ README pitch + submit. Buffer.

## Cut if time short (in order)
1. Voice Live
2. Memory/personalization (keep simple lens toggle)
3. Foundry IQ RAG (keep in-memory historical snippets)
4. Event Hubs (SSE replay from API directly)
5. Recap agent (compute on demand)
6. Swarm degrades: 15–20 particles with convergence easing, no full flocking

## Never cut
- Synthetic data + 4 agents with distinct roles (Numbers/Chalk/Booth/Pitch presentation)
- Evidence citations as the Evidence Spotlight (explainability is the core ask)
- Failure recovery demo (emergent, rehearsed)
- Frontend (balanced FE/BE) — the pitch-as-blackboard presentation
- Demo video ("The Verdict" film)

## Security & governance
- ACS YAML at input/LLM/state/tool/output checkpoints (PII filter, jailbreak protection, task adherence).
- Guided Guardrails in Foundry Agent Builder.
- Tracing for all agents.
- ASSERT evals over policies.
- Secrets: gitleaks + detect-private-key in pre-commit (in place); no keys in repo; Azure Key Vault / managed identity.
- Synthetic data only — no real PL data redistributed.

## Synthetic data format

Events are JSON objects:
```json
{
  "id": "evt_0042",
  "minute": 23,
  "second": 45,
  "type": "pass",
  "player": "Player A",
  "team": "Home",
  "position": {"x": 45.2, "y": 30.1},
  "end_location": {"x": 60.5, "y": 25.3},
  "outcome": "success",
  "metadata": {"pass_type": "through", "distance": 15.3, "body_part": "right_foot"}
}
```

Event types: `pass` (short/long/through/cross/back), `shot` (on_target/off_target/blocked/goal, with xG), `tackle`, `interception`, `foul` (yellow/red/no card), `possession_change`, `formation_change`, `substitution`, `set_piece` (corner/free_kick/penalty/throw_in), `goal` (with assist, type), `carry`, `pressure`.

## Microsoft Foundry integration (as built)
- GPT-5.4 via Azure OpenAI powers three paths: **Booth** narration (live
  Director path), **Verdict** recap (full time), and **Chalk's MAF reasoning
  loop** (tool-calling agent over the match toolkit).
- Chalk's toolkit is six deterministic models exposed as MAF tools; the model
  must cite real event ids and output is validated against the ledger.
- Every Foundry call (and every deterministic fallback) records a span
  (agent, model, tokens, status) surfaced at `/agentic/tracing`; `/health`
  reports Foundry availability.
- Graceful determinism: no credentials → identical output shapes, provenance
  shown, nothing pretends.
- Staged: the Booth as a Foundry hosted agent (`foundry-config/booth-agent.yaml`).
- Cut: Toolboxes (MCP), Foundry IQ RAG, Memory, ASSERT/ACS guardrails.

## Azure deployment (as built)
- **Azure Container Apps** for the API: self-contained Bicep (httpConcurrency
  scaling, health probe, `@secure()` Foundry key), `azure/deploy.sh` builds
  the image, creates an ACR, deploys, and prints the public endpoint.
- Cut: Event Hubs (SSE replay from the API directly), Azure Functions
  (agents run in-process; the MAF agent loop is the unit of parallelism).

## Immediate next steps
1. Scaffold `src/` (events, agents, api, frontend).
2. Implement synthetic generator first.
3. Build Scout + Analyst with evidence citations.
4. Add Director with A2A + failure recovery.
5. Build Next.js frontend.
6. Deploy + demo video + submit.
7. Keep pre-commit green on every commit.
