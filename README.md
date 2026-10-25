# Panna

AI-driven match intelligence for the **Microsoft Premier League "Inside the Game: Developer Hackathon."**

## What is this?

**Panna** transforms synthetic football events into explainable match intelligence, real-time narratives, automated recaps, and personalized experiences for fans, studios, broadcasters, and streaming platforms.

**Challenge:** [Inside the Game: Developer Hackathon](https://developer.microsoft.com/en-us/reactor/series/S-1709/) · **Prize pool:** $50,000 · **Hosted by:** Microsoft + Premier League

## Hackathon details

| Field | Value |
|---|---|
| **Theme** | Build AI-driven solutions that transform synthetic football events into explainable match intelligence for broadcast and streaming |
| **Data requirement** | Projects must use synthetic, football-realistic data. No real Premier League match data is redistributed. |
| **Submission period** | Oct 6 – Oct 27, 2026 (11:59 pm PT) |
| **Judging period** | Oct 27 – Nov 10, 2026 |
| **Winners announced** | No later than Nov 20, 2026 |
| **Format** | Online, individual or teams |
| **Prize pool** | $50,000 |

### Submission requirements

- Public GitHub repository
- Project pitch/description (what you built, Microsoft/Azure technologies used, what it does, what problem it solves)
- Demo video (<2 minutes) showing the project functioning on the device/platform it was built for
- Public URL to demo video on YouTube, Vimeo, Facebook Video, or Youku

### Judging criteria (20% each)

1. **Technological Implementation** — Quality software development, effective use of hero technologies, well-structured/maintainable code
2. **Agentic Design & Innovation** — Creative application of Agentic AI patterns, sophisticated multi-agent orchestration, novel AI implementation
3. **Real-World Impact & Applicability** — Significance of problem, production deployment readiness, potential impact
4. **User Experience & Presentation** — Well-designed UX, clear communication of value in demo, balanced frontend/backend
5. **Adherence to Hackathon Category** — Compliance with applicable category description

### Prize categories

| Prize | Amount (per team member) | What it targets |
|---|---|---|
| 🏆 Grand Prize: 1st Place | $4,000 + Premier League ticket + $50 voucher | Most complete and compelling solution |
| 🏆 Grand Prize: 2nd Place | $2,500 + Premier League ticket + $50 voucher | Runner-up most complete solution |
| 🧠 Best Use of Microsoft Foundry | $1,500 + $50 voucher | Most effective use of Microsoft Foundry for AI orchestration |
| 💼 Best Enterprise Solution | $1,500 + $50 voucher | Strongest readiness for enterprise deployment |
| 💡 Best Multi-Agent Orchestration | $1,500 + $50 voucher | Purposeful multi-agent collaboration with distinct roles, shared state, handoffs, failure recovery |
| 🎨 Best Azure Cloud Native Integration | $1,500 + $50 voucher | Best use of Azure cloud-native services (AKS, ACA, Functions, Logic Apps, AI data platforms) |

## Project concept

**Panna** is a multi-agent match intelligence engine that transforms synthetic football events into real-time, explainable match intelligence for broadcast and streaming platforms.

### The 4-agent pipeline

**Presentation identity:** *Numbers see it, Chalk proves it, Booth says it* — and the
pitch itself is the fourth actor. The interface is the match surface: agents coordinate
through a shared blackboard (the pitch), leaving chalk traces rather than sending
messages. See [docs/design-vision.md](docs/design-vision.md) for the full design language
and the demo film script ("The Verdict").

| Agent | Presentation | Role | Output |
|---|---|---|---|
| **Scout** | **Numbers** (the swarm) | Watches the synthetic event stream, flags key moments (shots, tackles, possession shifts, formation changes) | Structured event markers with timestamps and evidence citations |
| **Analyst** | **Chalk** (the specialists) | Computes tactical insights (xG, formation effectiveness, pressing intensity, player influence, momentum shifts) | Statistical insights with evidence citations (which events led to this conclusion) |
| **Commentator** | **Booth** | Generates natural-language broadcast commentary from Scout + Analyst output | Live commentary text with timing, tone, and narrative arc |
| **Director** | **the Pitch** (coordination as a place) | Orchestrates all three agents, decides what to surface and when, handles failure recovery | Curated broadcast feed with prioritized insights |

### Why this wins

The judging rubric scores 5 categories at 20% each. Panna targets **4 prize categories simultaneously**:

1. **Grand Prize** — most complete and compelling solution
2. **Best Multi-Agent Orchestration** — 4 agents with distinct roles, shared state, handoffs, failure recovery
3. **Best Use of Microsoft Foundry** — Foundry orchestrates the 4-agent pipeline
4. **Best Azure Cloud Native Integration** — Azure Container Apps + Event Hubs + Functions

### Microsoft tech stack (2026 hero tech — see docs/critique.md)

- **Microsoft Agent Framework (MAF)** — Magentic-One multi-agent orchestration, A2A handoffs, shared state, failure recovery; integrates GitHub Copilot SDK
- **Microsoft Foundry Agent Service** (GA) — hosted agents with sandboxed sessions, state, filesystem; Responses API + Invocations protocol
- **Foundry Toolboxes (MCP)** — single governed endpoint for tools/skills/enterprise data
- **Foundry IQ** (GA knowledge bases) + **Web IQ** — SLA-backed RAG replacing custom Azure AI Search plumbing
- **Foundry Memory** (public preview) — procedural/user/session memory for personalization
- **Enterprise controls** — Tracing (any framework), ASSERT evals, Agent Control Specification (ACS) guardrails, Guided Guardrails, Rubric
- **Azure Container Apps** — FastAPI API (serverless, event-driven)
- **Azure Functions** — serverless agents runtime (per-agent workers)
- **Azure Event Hubs** — synthetic event stream ingestion
- **Models** — GPT-5.4 / GPT-5.4 Pro via Model Router (or MAI-Thinking-1); Voice Live optional
- **Frontend** — Next.js: the pitch *is* the interface (chalk telestration, boids swarm, pitch-control glow, Ceefax-style ticker, lens switching)
- **GitHub Copilot** — development

### Synthetic data

Projects must use synthetic, football-realistic data. No real Premier League match data is redistributed. Panna generates synthetic events including:
- Passes (short, long, through, cross) with player positions and timestamps
- Shots (on target, off target, blocked) with xG values
- Tackles, interceptions, fouls
- Possession changes and momentum shifts
- Formation changes and substitutions
- Set pieces (corners, free kicks, penalties)

### Explainability

Every insight comes with evidence citations — which events led to this conclusion.
On screen, evidence is shown as an **Evidence Spotlight**: the pitch dims, cited
events glow gold, and chalk lines draw themselves from the claim to its sources.
This is what makes it "explainable match intelligence" — the hackathon's core ask.

## Relationship to SportWarren

Panna is built as a **separate project** for the hackathon. After judging, the following capabilities will be merged into SportWarren:

- Synthetic data pipeline → feeds SportWarren's match simulation engine
- Multi-agent commentary → replaces deterministic commentary with LLM-based
- Tactical insights → enhanced with broadcast-grade explainability
- Microsoft Foundry → replaces OpenAI/Anthropic with Azure OpenAI
- Azure deployment → adds Azure as a deployment target alongside Vercel

## Build plan (compressed — see docs/strategy.md + docs/design-vision.md, deadline Oct 27 2026)

### Day 1 (Oct 25) — core pipeline + frontend scaffold ✅
- Synthetic data generator (StatsBomb-like schema, seeded match) + real xG/PPDA/formation models
- Scout + Analyst agents (MAF, Foundry GPT-5.4) with evidence citations
- Commentator agent (timed broadcast NL) + Director (A2A orchestration, shared state, failure recovery)
- Next.js frontend v1 (shipped in scaffold commit; superseded by the Day 2 vision build)

### Day 2 (Oct 26) — the vision build + cloud + polish + submit
Frontend rebuilt around [docs/design-vision.md](docs/design-vision.md) v2 — *the pitch is
the blackboard*, and the demo is a forensic film, "The Verdict":
1. SSE stream + replay clock + rewind/freeze/failure-injection controls
2. Pitch SVG + chalk telestration + Evidence Spotlight
3. Boids swarm (~40–80 particles, flocking + quorum hardening)
4. Pitch-control glow + momentum/xG charts
5. Ticker band + score bug + lens switching
6. Failure/recovery choreography · 7. Recap as annotated board · 8. On-air seed regeneration

Cloud: API to ACA; agents to Foundry hosted agents; Event Hubs; Foundry IQ; tracing/ACS.
Then demo video (<2 min, scripted) + README pitch + submit.

### Cut if time short (in order)
1. Voice Live
2. Memory/personalization (keep lens toggle)
3. Foundry IQ RAG (in-memory snippets)
4. Event Hubs (SSE replay from API)
5. Recap agent (on demand)
6. Swarm degrades to simple particle convergence (chalk never cut)

### Never cut
- Synthetic data + 4 agents with distinct roles (Numbers/Chalk/Booth/Pitch presentation)
- Evidence citations via the Evidence Spotlight (explainability is the core ask)
- Failure recovery demo (emergent, rehearsed)
- Frontend (balanced FE/BE)
- Demo video ("The Verdict")

## Project structure

```
panna/
├── README.md
├── .gitignore
├── .pre-commit-config.yaml
├── docs/
│   ├── strategy.md       # Revised build plan
│   ├── critique.md       # Research-backed tech-stack critique
│   └── design-vision.md  # v2: pitch-as-blackboard design language + "The Verdict" demo film
├── pyproject.toml
├── src/
│   ├── events/           # Synthetic event generator
│   ├── agents/
│   │   ├── scout.py      # "Numbers" — event detection + key moment flagging
│   │   ├── analyst.py    # "Chalk" — tactical insights with evidence citations
│   │   ├── commentator.py # "Booth" — timed broadcast commentary
│   │   ├── director.py   # coordination, failure recovery
│   │   └── recap.py      # post-match recap (Day 2)
│   ├── foundry/          # Foundry hosted agents, Toolboxes, IQ, Memory
│   ├── azure/            # ACA, Functions, Event Hubs, deployment config
│   ├── models/           # xG, PPDA, formation, influence, momentum
│   ├── api/              # FastAPI service (incl. SSE replay stream)
│   └── frontend/         # Next.js — pitch-as-blackboard interface
└── ...
```

## Running locally

```bash
# Backend (FastAPI)
pip install fastapi uvicorn pydantic
make backend          # http://localhost:8000  (docs at /docs)

# Frontend (Next.js)
cd frontend && npm install && npm run dev   # http://localhost:3000

# Full pipeline CLI
make run-pipeline

# Tests / lint
make test
make lint
```

Environment variables (see `.env.example`): `FOUNDRY_ENDPOINT`, `FOUNDRY_API_KEY`, `FOUNDRY_DEPLOYMENT`.

## Links

- Challenge: https://developer.microsoft.com/en-us/reactor/series/S-1709/
- Rules: https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md
- Synthetic data: https://github.com/microsoft/insidethegamehackathon
