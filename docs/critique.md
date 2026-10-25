# Panna — Tech-stack & build-plan critique (research-backed)

> Research performed 2026-10-25 via Tavily. Sources cited inline. Submission deadline is **Oct 27, 2026 11:59 pm PT** — ~2 days from now, so this doc is written to be executable, not aspirational.
>
> **Note (2026-10-25, evening):** this doc is a research snapshot. `docs/design-vision.md`
> (v2) supersedes all *frontend/presentation* statements here — notably "insight cards with
> evidence chips" and "My Lens toggle", which became the pitch-as-blackboard visual language
> (chalk telestration, boids swarm, Evidence Spotlight, lens switching). Backend/stack
> findings below remain current.

## 1. What the hackathon actually rewards (from official rules)

Judging (20% each): **Technological Implementation · Agentic Design & Innovation · Real-World Impact & Applicability · User Experience & Presentation · Adherence to Hackathon Category**.

Prize categories (each $1,500 + voucher per member):
- 🏆 Grand Prize 1st/2nd (most complete + compelling, innovative use of Microsoft AI platform)
- 🧠 Best Use of Microsoft Foundry (faster innovation, developer productivity, scalable AI hard to achieve otherwise)
- 💼 Best Enterprise Solution (production readiness, reliability, transparency, controls)
- 💡 Best Multi-Agent Orchestration (distinct roles, shared state, handoffs, failure recovery, end-to-end outcome a single agent can't match)
- 🎨 Best Azure Cloud Native Integration (AKS/ACA/Functions/Logic Apps/AI data platforms, event-driven, operational excellence)

Submission must include: newly built project meeting requirements; pitch; <2-min demo video showing it running on target device/platform; public GitHub repo.

**Key insight:** a "generic 4-agent pipeline" only cleanly wins 💡 Multi-Agent. To win 🧠 Foundry and 🎨 Azure Cloud Native and 💼 Enterprise, the stack must *visibly* use Foundry-hosted agents, Toolboxes, Foundry IQ, Azure Functions/ACA/Event Hubs, and enterprise controls (tracing, guardrails, ACS). To win 🏆 Grand, need a polished frontend + clear narrative + demo.

## 2. Research findings — what "current" Microsoft stack looks like (Oct 2026)

From Microsoft Foundry "Build Edition" (June 2026) and related sources:

- **Microsoft Agent Framework (MAF)** is now the hero orchestration layer: stable agent harness with skills/memory/middleware, **Magentic-One multi-agent pattern**, integrations with **GitHub Copilot SDK** and Claude Agent SDK, A2A protocol support.
- **Foundry Agent Service** reached GA (March 16, 2026): Responses-API-based, private networking, MCP auth (incl. OAuth passthrough), hosted agents (GA early July 2026) with sandboxed sessions, state, filesystem, framework-agnostic (MAF/LangGraph/Copilot SDK).
- **Two protocols**: Responses API (stateful OpenAI-compatible) and **Invocations protocol** (schema-free pass-through where you control request/response) — useful for custom event payloads.
- **Toolboxes** (public preview): single governed endpoint for tools/skills/MCP clients + enterprise data; connects to Microsoft IQ (Work IQ / Fabric IQ / Foundry IQ).
- **Foundry IQ** (GA knowledge bases): SLA-backed retrieval, MCP access, multi-source (Work/Fabric/File/Azure SQL/MCP), replaces custom RAG. **Web IQ** for sub-200ms live web grounding.
- **Memory** (public preview): procedural (+7–14% task success), user, session — enables personalized fan experience.
- **Voice Live** (GA for prompt agents): real-time speech/TTS/avatars — potential broadcast-voice differentiator.
- **Azure Functions** shipped a **serverless agents runtime** at Build 2026 (InfoQ) — per-agent serverless processing, ideal for Scout/Analyst/Commentator/Writer as Functions.
- **Foundry IQ + Toolboxes + MCP** is the intended "AI data platform" for 🎨 prize.
- **Enterprise controls**: **ASSERT** (open-source policy→evals), **Agent Control Specification (ACS)** (YAML controls at input/LLM/state/tool/output checkpoints), Guided Guardrails, Rubric evaluator, tracing for any framework, Agent Optimizer. These map directly to 💼 Best Enterprise Solution + "explainable" requirement.
- **Models**: GPT-5.4/GPT-5.4 Pro GA, MAI family (Thinking-1, Image-2.5, Transcribe-2, Voice-2), Fireworks AI on Foundry (open models), Model Router.
- **A2A protocol** supported by MAF for cross-agent handoffs (judges explicitly list A2A as a recognized orchestration approach).

## 3. Critique of the current plan

### 3.1 Tech stack is outdated / not aligned to 2026 hero tech

| Current (README/docs) | Problem | Modern replacement |
|---|---|---|
| "Azure OpenAI (GPT-4o)" via Foundry | GPT-4o is last-gen; judges look for current models | GPT-5.4 / GPT-5.4 Pro (GA) or MAI-Thinking-1; use Model Router |
| "Azure Container Apps + Event Hubs + Functions" (generic) | No use of Foundry Agent Service, Toolboxes, Foundry IQ, A2A | Foundry hosted agents + Toolboxes + Foundry IQ + A2A + Event Hubs + ACA (API) + Functions (per-agent) |
| "Azure AI Search for RAG" | Custom RAG plumbing; Foundry IQ is the 2026 hero | Foundry IQ knowledge bases (GA) + Web IQ |
| "Microsoft Foundry orchestrates" (vague) | No concrete Foundry primitives named | Hosted agents, Toolboxes, Memory, Tracing/ASSERT, Guardrails |
| No frontend | UX criterion (20%) demands balanced FE/BE | React/Next.js live match dashboard |
| No observability/governance | Enterprise prize + explainability | Tracing + ACS YAML + ASSERT evals |
| No personalization | "personalized experiences" in brief | Foundry Memory (user/session) |
| No recaps | "automated recaps" in brief | Post-match recap agent + endpoint |
| No voice | "narratives for broadcasters" | Voice Live (optional, high-impact) |

### 3.2 Build plan is too generic

- "Synthetic event generator" with no schema fidelity → judges can't see realism. Need StatsBomb-like event schema (passes with end locations, shots with xG, pressures, carries, formations) and a seeded deterministic match.
- "Scout flags key moments" → no evidence-citation contract. Need every insight to carry `evidence: [event_ids]` and a retrievable trail (Foundry IQ / in-memory store).
- "Analyst computes xG" → xG must be a real model (distance/angle + body part), not a constant. Formation effectiveness, pressing intensity (PPDA), player influence (network centrality / xT), momentum (rolling xG window).
- "Commentator generates text" → must be timed to events, broadcast tone, and cite insights. Use GPT-5.4 with structured output + timing.
- "Director orchestrates" → must show *actual* orchestration (A2A handoffs, shared state, failure recovery with retries/fallback), not a sequential script. This is the 💡 prize core.
- Missing: failure-recovery demo (kill one agent → others continue) — explicitly judged.
- Missing: demo video plan and frontend.

### 3.3 Scope risk (2 days)

Original 48h plan assumed Day1/Day2 with buffer. Reality: submission closes Oct 27. Must cut aggressively. Recommended MVP below.

## 4. Revised architecture (hero-tech aligned)

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Next.js on Vercel/Azure Static Web Apps)         │
│  Live match feed · Insight cards (with evidence) ·           │
│  Commentary stream · Recap · Personalized "My Lens"          │
└──────────────┬──────────────────────────────────────────────┘
               │ HTTPS
┌──────────────▼──────────────────────────────────────────────┐
│  API (Azure Container Apps) — FastAPI                       │
│  /matches /events /insights /commentary /recap /personalize │
└────┬─────────────┬──────────────┬───────────────────────────┘
     │             │              │
     ▼             ▼              ▼
 Event Hubs   Foundry Agent Service (hosted agents, MAF)
 (synthetic    ├─ Scout agent   (event detection, key moments)
  stream)      ├─ Analyst agent (xG, PPDA, formation, influence, momentum)
               ├─ Commentator  (timed broadcast NL, cites insights)
               ├─ Recap agent  (post-match summary)
               └─ Director     (A2A orchestration, prioritization, recovery)
                      │
                      ├── Toolboxes (MCP) → Foundry IQ (historical context)
                      ├── Memory (user/session/personalization)
                      ├── Tracing + ASSERT + ACS (governance/explainability)
                      └── Voice Live (optional broadcast voice)
     │
     ▼
 Azure Functions (per-agent serverless workers)  +  Azure AI Search/Foundry IQ
```

Shared state: a match-state store (Cosmos DB or in-memory + Redis) holding events, insights, commentary, agent health. A2A messages carry match context; Foundry Memory persists fan prefs.

Explainability contract: every insight = `{id, type, claim, value, confidence, evidence: [event_ids], agent, timestamp}`. UI renders evidence as clickable chips → highlights source events.

Failure recovery: Director wraps each agent call in try/except with timeout, retries (backoff), and a degraded-mode fallback (e.g., Analyst down → Scout still surfaces raw key moments; Commentator falls back to template). Emit agent-health events to frontend.

## 5. Revised 48h plan (compressed, deadline Oct 27)

### Day 1 (Oct 25) — core pipeline + frontend
- Morning: Synthetic data generator (StatsBomb-like schema, seeded match, ~90 min, ~1500 events) + xG/PPDA/formation models. Commit.
- Midday: Scout + Analyst agents (MAF, Foundry GPT-5.4), evidence citations. Local run.
- Afternoon: Commentator agent (timed, broadcast tone) + Director (A2A orchestration, shared state, failure recovery).
- Evening: Next.js frontend (live feed, insight cards with evidence, commentary panel). End-to-end local test.

### Day 2 (Oct 26) — cloud + polish + submit
- Morning: Deploy API to ACA, agents to Foundry hosted agents, Event Hubs ingestion, Foundry IQ for historical context, tracing/ACS. (Cut Event Hubs if time → polling.)
- Midday: Recap agent + personalized "My Lens" (Memory). Voice Live only if time.
- Afternoon: Demo video (<2 min) + README pitch + submit. Buffer.

### Cut if time short (in order)
1. Voice Live (nice-to-have)
2. Memory/personalization (keep a simple prefs toggle)
3. Foundry IQ RAG (keep in-memory historical snippets)
4. Event Hubs (polling)
5. Recap agent (compute on demand)

### Never cut
- Synthetic data + 4 agents with distinct roles
- Evidence citations (explainability is the core ask)
- Failure recovery demo
- Frontend (balanced FE/BE for UX score)
- Demo video

## 6. Judging optimization matrix

| Criterion (20%) | How Panna scores it |
|---|---|
| Technological Implementation | FastAPI + Next.js, typed (Pydantic), ruff/pre-commit, tests, Foundry hosted agents, ACA, Event Hubs, Functions, Foundry IQ, tracing |
| Agentic Design & Innovation | MAF Magentic-One + A2A handoffs, shared state, failure recovery, memory, toolboxes — single agent cannot do this |
| Real-World Impact | Production patterns: ACS guardrails, tracing, evals (ASSERT), enterprise controls, ACA serverless |
| UX & Presentation | Live dashboard with evidence chips, commentary stream, recap, <2-min demo video with clear narrative |
| Adherence to Category | Synthetic data only, explainable insights with citations, real-time narratives, automated recaps, personalization |

## 7. Security & governance (for 💼 + explainability)

- ACS YAML contract at input/LLM/state/tool/output checkpoints (PII filter, jailbreak protection, task adherence).
- Guided Guardrails enabled in Foundry Agent Builder.
- Tracing for all agents (Foundry tracing, framework-agnostic).
- ASSERT evals over policies (e.g., "no fabricated events", "every claim cites ≥1 event").
- Secrets: gitleaks + detect-private-key in pre-commit (already in place); no keys in repo; use Azure Key Vault / Foundry managed identity.
- Synthetic data only — no real PL data redistributed.

## 8. Immediate next steps

1. Replace README tech stack section with §4 (hero tech).
2. Replace docs/strategy.md checklist with §5 compressed plan.
3. Scaffold `src/` per §4 (events, agents, api, frontend).
4. Implement synthetic generator first (everything depends on it).
5. Keep pre-commit green on every commit.

## Sources

- Microsoft Foundry "What's new" Build Edition (June 2026): https://devblogs.microsoft.com/foundry/whats-new-in-microsoft-foundry-build-2026
- Microsoft Foundry March 2026 update: https://devblogs.microsoft.com/foundry/whats-new-in-microsoft-foundry-mar-2026
- July/August 2026 update: https://devblogs.microsoft.com/foundry/whats-new-in-microsoft-foundry-july-august-2026
- InfoQ: "Microsoft Foundry Adds Runtime, Tooling, and Governance for Production Agents" (2026): https://www.infoq.com/news/2026/06/microsoft-foundry-agents
- InfoQ: "Azure Functions Ships Serverless Agents Runtime at Build 2026": https://www.infoq.com/news/2026/06/azure-functions-serverless-agent
- InfoQ: "Microsoft Agent Framework Harness and Hosted Agents Reach GA": https://www.infoq.com/news/2026/08/agent-framework-harness-ga
- Microsoft Cloud blog: A2A protocol support: https://www.microsoft.com/en-us/microsoft-cloud/blog/2025/05/07/empowering-multi-agent-apps-with-the-open-agent2agent-a2a-protocol
- Microsoft Agent Framework A2A guest blog: https://devblogs.microsoft.com/agent-framework/guest-blog-building-multi-agent-solutions-with-semantic-kernel-and-a2a-protocol
- Official hackathon rules: https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md
- Challenge: https://developer.microsoft.com/en-us/reactor/series/S-1709/
