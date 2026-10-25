# Panna — Build strategy (revised 2026-10-25)

> Supersedes the original generic plan. See `docs/critique.md` for the research-backed rationale.
> **Deadline: Oct 27, 2026 11:59 pm PT. Today is Oct 25 — ~2 days.**

## Goal

Win multiple prize categories simultaneously by visibly using 2026 Microsoft hero tech:
Foundry hosted agents (MAF + Magentic-One + A2A), Toolboxes, Foundry IQ, Azure Functions
serverless agent runtime, ACA, Event Hubs, Memory, Tracing/ACS/ASSERT, plus a polished
Next.js frontend. Synthetic football data only. Every insight carries evidence citations.

## Revised tech stack (hero-tech aligned)

- **Orchestration:** Microsoft Agent Framework (MAF) — Magentic-One multi-agent pattern, A2A handoffs, shared state, failure recovery. Integrates GitHub Copilot SDK.
- **Agent runtime:** Foundry Agent Service (GA) hosted agents — sandboxed sessions, state, filesystem, framework-agnostic. Protocols: Responses API + Invocations.
- **Tools/data:** Foundry Toolboxes (MCP) → Foundry IQ knowledge bases (GA) + Web IQ. Replaces custom RAG.
- **Personalization:** Foundry Memory (procedural/user/session).
- **Enterprise controls:** Tracing (any framework), ASSERT evals, ACS YAML guardrails, Guided Guardrails, Rubric evaluator.
- **Compute:** Azure Container Apps (FastAPI API) + Azure Functions (per-agent serverless workers) + Azure Event Hubs (synthetic stream ingestion).
- **Models:** GPT-5.4 / GPT-5.4 Pro via Model Router (or MAI-Thinking-1). Voice Live optional.
- **Frontend:** Next.js live match dashboard (evidence chips, commentary stream, recap, "My Lens").
- **Data:** synthetic StatsBomb-like event schema, seeded deterministic match (~90 min, ~1500 events), real xG/PPDA/formation models.

## The 4-agent pipeline (plus Recap)

| Agent | Role | Output |
|---|---|---|
| **Scout** | Watches synthetic stream; flags key moments (shots, tackles, possession shifts, formation changes, set pieces) | Structured markers: `{event_id, minute, type, importance, evidence:[event_ids]}` |
| **Analyst** | Computes tactical insights: xG per shot (distance/angle/body part), PPDA pressing intensity, formation effectiveness, player influence (xT/network), momentum (rolling xG) | Insights: `{id, type, claim, value, confidence, evidence:[event_ids]}` |
| **Commentator** | Timed broadcast NL from Scout+Analyst, cites insights, professional tone | Commentary entries with minute/second timing |
| **Director** | A2A orchestration, prioritization, shared state, failure recovery (retry + degraded fallback), agent health | Curated broadcast feed |
| **Recap** (Day2) | Post-match summary from all above | Recap text + top insights |

## Explainability contract

Every insight = `{id, type, claim, value, confidence, evidence: [event_ids], agent, timestamp}`. UI renders evidence as clickable chips that highlight source events. ASSERT evals enforce "every claim cites ≥1 event" and "no fabricated events".

## Failure recovery (explicitly judged)

Director wraps each agent call in try/except with timeout + exponential backoff retry + degraded-mode fallback:
- Analyst down → Scout still surfaces raw key moments; Commentator falls back to template.
- Commentator down → insights still published.
- Emit agent-health events to frontend (green/amber/red per agent).

## Compressed 48h plan

### Day 1 (Oct 25) — core pipeline + frontend
- Morning: Synthetic data generator (StatsBomb-like schema, seeded match) + xG/PPDA/formation models. Commit.
- Midday: Scout + Analyst agents (MAF, Foundry GPT-5.4), evidence citations. Local run.
- Afternoon: Commentator agent (timed, broadcast tone) + Director (A2A orchestration, shared state, failure recovery).
- Evening: Next.js frontend (live feed, insight cards with evidence, commentary panel). End-to-end local test.

### Day 2 (Oct 26) — cloud + polish + submit
- Morning: Deploy API to ACA, agents to Foundry hosted agents, Event Hubs ingestion, Foundry IQ, tracing/ACS. (Cut Event Hubs → polling if time.)
- Midday: Recap agent + "My Lens" personalization (Memory). Voice Live only if time.
- Afternoon: Demo video (<2 min) + README pitch + submit. Buffer.

## Cut if time short (in order)
1. Voice Live
2. Memory/personalization (keep simple prefs toggle)
3. Foundry IQ RAG (keep in-memory historical snippets)
4. Event Hubs (polling)
5. Recap agent (compute on demand)

## Never cut
- Synthetic data + 4 agents with distinct roles
- Evidence citations
- Failure recovery demo
- Frontend (balanced FE/BE)
- Demo video

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

## Microsoft Foundry integration
- Use GPT-5.4 via Model Router for agent reasoning.
- Each agent is a Foundry hosted agent with its own system prompt + tools via Toolboxes (MCP).
- Shared state via match-state store; A2A messages carry context.
- Foundry IQ for historical match context (RAG).
- Memory for fan personalization.
- Tracing + ASSERT + ACS for governance/explainability.

## Azure deployment
- **Azure Container Apps** for the API (event-driven, serverless).
- **Azure Event Hubs** for synthetic event stream ingestion.
- **Azure Functions** for individual agent processing (serverless agents runtime).
- **Foundry IQ** for RAG (historical match context).

## Immediate next steps
1. Scaffold `src/` (events, agents, api, frontend).
2. Implement synthetic generator first.
3. Build Scout + Analyst with evidence citations.
4. Add Director with A2A + failure recovery.
5. Build Next.js frontend.
6. Deploy + demo video + submit.
7. Keep pre-commit green on every commit.
