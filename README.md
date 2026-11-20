# Panna

AI-driven match intelligence for the **Microsoft Premier League "Inside the Game: Developer Hackathon."**

## What is this?

**Panna** transforms synthetic football events into explainable match intelligence, real-time narratives, automated recaps, and personalized experiences for fans, studios, broadcasters, and streaming platforms.

**Challenge:** [Inside the Game: Developer Hackathon](https://developer.microsoft.com/en-us/reactor/series/S-1709/) · **Prize pool:** $50,000 · **Hosted by:** Microsoft + Premier League

**Live demo:** <https://panna.sportwarren.com> — open the app, or jump straight into a match
(e.g. <https://panna.sportwarren.com/?match=match_63&seed=63>). Every match is
deterministic from its seed, so any shared URL replays the same game.

**For judges:** [docs/JUDGES.md](docs/JUDGES.md) is the 3-minute path ·
[docs/PROOF.md](docs/PROOF.md) is the trust architecture ·
[docs/CLAIMS.md](docs/CLAIMS.md) is the honest real-vs-staged ledger ·
[docs/post-hackathon-strategy.md](docs/post-hackathon-strategy.md) is where
the verified/trusted-AI market opportunity is mapped (EU AI Act Art 50 + EAA) ·
`GET /status` reports it live.

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

### The 5-agent pipeline (with an air-gate)

**Presentation identity:** *Numbers see it, Chalk proves it, Booth says it, the Gate
keeps it honest* — and the pitch itself is the coordination surface. Agents coordinate
through a shared blackboard (the pitch), leaving chalk traces rather than sending
messages. See [docs/design-vision.md](docs/design-vision.md) for the full design language
and the demo film script ("The Verdict").

| Agent | Presentation | Role | Output |
|---|---|---|---|
| **Scout** | **Numbers** (the swarm) | Watches the synthetic event stream, flags key moments (shots, tackles, possession shifts, formation changes) | Structured event markers with timestamps and evidence citations |
| **Analyst** | **Chalk** (the specialists) | Computes tactical insights (xG, formation effectiveness, pressing intensity, player influence, momentum shifts) | Statistical insights with evidence citations (which events led to this conclusion) |
| **Commentator** | **Booth** | Generates natural-language broadcast commentary from Scout + Analyst output | Live commentary text with timing, tone, and narrative arc |
| **Verifier** | **the Gate** | Deterministic recount — code, not a model. Recomputes every stat, score, minute, and attribution from the raw ledger; repairs fixable claims; **fails closed** on the rest | Per-line verdicts (`verified`/`repaired`/`rejected`) + the producer hold queue |
| **Director** | **the Pitch** (coordination as a place) | Orchestrates all agents, inserts the Verifier between drafted lines and air, decides what to surface and when, handles failure recovery | Curated broadcast feed with prioritized insights |

**Let AI tell the story, let code keep the score.** Every insight and commentary line
carries a verdict from the Gate. Rejected lines never reach the screen — they wait in
the producer's hold queue at `/producer?match={id}` for a human approve/kill. Plant a
lie yourself: `POST /stream/playback/{match}` `{action:"seed_bad_claim"}` injects a
fabricated score + invented stat and watches the gate refuse them. Proof and measured
catch rates: [docs/PROOF.md](docs/PROOF.md) ·
[reports/verifier-redteam.md](reports/verifier-redteam.md).

### Why this wins

The judging rubric scores 5 categories at 20% each. Panna targets **4 prize categories simultaneously**:

1. **Grand Prize** — most complete and compelling solution
2. **Best Multi-Agent Orchestration** — 4 agents with distinct roles, shared state (the pitch blackboard), staggered reveals, failure recovery
3. **Best Use of Microsoft Foundry** — GPT-5.4 narrates the Booth, reasons the Verdict, and powers Chalk's MAF tool loop; every call traced, every fallback honest
4. **Best Azure Cloud Native Integration** — ACA deployment with httpConcurrency scaling, health probes, and a reproducible one-command deploy

### Microsoft tech stack — what is real, what is staged

**Live in this repo (verifiable in code, tested):**
- **Microsoft Agent Framework (MAF)** — Chalk's reasoning is an MAF agent
  (`agent_framework.Agent` on Azure OpenAI) that reads the match through a
  six-function toolkit (xG, PPDA, formation, influence, momentum, event
  windows) in a tool-calling loop, then files JSON insights that are
  re-validated against the event ledger before they reach the board. Every
  model tool call is traced (`/agentic/tracing`). `src/foundry/maf.py`.
- **Microsoft Foundry models** — GPT-5.4 via Azure OpenAI: the Booth narrates
  the live commentary, Chalk reasons the insights, the Verdict writes the
  full-time recap. Every call records a span (agent, model, tokens, status).
  `src/foundry/{client,agents,narrative,maf}.py`.
- **Graceful determinism** — with no Foundry credentials, the identical
  Insight/Commentary shapes are produced by the deterministic models, so the
  product, tests, and demo never depend on the network. The header shows
  which path ran (provenance), never pretending.
- **The Verifier gate** — every broadcast item is recounted by deterministic
  code *independent of the agents that wrote it* before it may air
  (`src/agents/verifier.py`): stats, scorelines, minutes and attribution
  recount from the raw ledger; decimals in evidence-bound insights must come
  from the cited events, not anywhere in the match; betting/certainty/
  real-league wording is banned outright; causal wording ("because", "cost
  them") fails closed until a sim model exists to back it; lines capped at
  240 chars. Verified lines carry a `✓ verified` chip with a "why?" panel;
  repairable errors air corrected (`✎ repaired`, original retained in the
  audit); the rest are held for the producer. The gate cannot be darkened in
  the failure demo — it is the part that is *not* a model.
- **Producer console** — `/producer?match={id}` lists every line, verdict,
  and air status; approve/kill is real (`/producer/{match}/decide`). Red-team
  demo built in: one click plants fabricated lines and watches them held.
- **Audit ledger** — every verdict, air/suppress outcome, and producer
  decision appends to JSONL (`src/audit.py`, `PANNA_AUDIT_PATH`) so "what
  aired, what was held, who approved it?" is answerable after the process
  dies. Fail-soft: an audit write can never take the broadcast down.
- **Spoken audio** — `POST /audio/speak` voices a verified line through
  Azure AI Speech (key or Entra). Unconfigured it 503s honestly; the
  always-on text AD feed remains the fallback. `src/foundry/speech.py`.
- **Feeds for every fan** — each SSE connection renders the verified
  broadcast for its viewer (`src/feed.py`): `?lang=es|fr|pt|de` localizes via
  Azure AI Translator (`src/foundry/translate.py`, key or Entra auth,
  per-match cache) *after* the gate, so nothing unverified airs in any
  language — and `?audience=kids|ad` reshapes it: kids get jargon-free lines,
  `ad` is a genuine audio-description track generated deterministically from
  event positions, outcomes and body part (`src/events/audio.py`), always on
  with no credentials. Every translated line is re-checked before it airs —
  numbers and player names must survive verbatim — so a mangled translation
  falls back to the verified original (`translation_problem` in the payload).
  Unconfigured Translator serves the original text labelled
  `translation=original` — honest, never silent.
- **Keyless Azure auth** — managed identity + `DefaultAzureCredential` mint
  Entra tokens for the Foundry endpoint (and Translator via
  `TRANSLATOR_AUTH=entra`); the Bicep module assigns
  `Cognitive Services OpenAI User` to the container app's identity. No stored
  secrets. API-key env auth remains for local dev.
- **Cost guard + ledger** — the matchday auto-pauses when the last viewer
  disconnects and resumes when one returns (agents only spend when watched);
  `GET /status` reports per-match tokens + estimated spend.
- **Azure Container Apps** — the API ships as a container with a
  self-contained Bicep module (system-assigned identity, httpConcurrency
  scaling, health probe) and a one-command `azure/deploy.sh` (build → ACR →
  deploy → public endpoint). `Dockerfile`, `azure/`.

**Staged (definition ready, executes once an Azure subscription is attached):**
- **Foundry hosted agent** — the Booth as a hosted agent definition
  (instructions, toolbox, memory, tracing, guardrails) in
  `foundry-config/booth-agent.yaml`.

**Elsewhere in the stack:** GPT-5.4 via Azure OpenAI (Model Router) ·
Next.js frontend (the pitch *is* the interface) · GitHub Copilot for
development.

**Deliberately cut from scope (honest, not hidden):** A2A handoffs,
Magentic-One, Event Hubs, Azure Functions, Foundry IQ, Foundry Memory. The
pipeline is a shared-state blackboard (stigmergy) by design, and the
transport is SSE, not Event Hubs. These were on the Day-1 stack and were
cut for depth; they are **not** claimed here.

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

### Interoperability

The platform is built so the match can be consumed outside the Panna frontend:

- **One canonical event frame.** REST (`GET /events/{id}`), the SSE stream, and
  the MCP server all emit the same flat StatsBomb-like frame
  (`id, type, team, minute, x, y, end_x, end_y, outcome, xg`). No client-side
  shape reconciliation.
- **Seed-deterministic matches.** Any consumer can regenerate any match from
  `match_<seed>` — the match is addressable without our server.
- **MCP server.** The match is exposed as a queryable toolkit over the
  **Model Context Protocol**, so any MCP client (Copilot, Claude Desktop, a
  custom agent) can pull a match by seed and verify its evidence:
  `match_info`, `match_events`, `team_summary`, `match_insights`,
  `event_details` — plus `verify_line`, which runs the broadcast Verifier over
  any prose so an external agent can audit a claim without trusting Panna.
  ```bash
  panna-mcp                 # run the MCP server (stdio transport)
  ```
- **Self-contained artifacts.** `/share/{id}` returns a standalone HTML
  case file (no external assets) that opens from a plain file.
- **Open transport.** CORS is open. Both halves are containers with
  Dockerfiles (API and `frontend/`), so the whole product runs on any container
  host, not just Azure — a reverse proxy pointing a domain at the two containers
  is all it takes to go live.

### Accessibility

The pitch is designed to be understood without color or motion:

- **Shape, not just color.** Teams are encoded by shape as well as hue — Home
  is solid lines with filled shot rings, Away is dashed lines with open rings
  (WCAG 1.4.1). A visible legend states the mapping.
- **Text alternatives for the board.** The pitch SVG carries a `role="img"`
  title + description; the momentum chart is labeled; the score bug announces
  score, minute, and state.
- **Live updates for screen readers.** Goals and score changes are announced
  via an `aria-live` region; the swarm canvas is `aria-hidden` (decorative).
- **Reduced motion.** `prefers-reduced-motion` disables chalk draws, pulses,
  ticker, and goal flashes.
- **Keyboard + focus.** All controls are focusable with a visible
  `:focus-visible` outline; insight strips are keyboard-operable.
- **Responsive.** The board and verdict collapse to a single column under
  900px.

### Known constraints (honest)

- **State is in-memory, single-replica.** Matches, sessions, and traces live
  in process memory. Scale ACA to >1 replica and a `/generate` on one instance
  isn't visible to a `/stream` on another (seed-determinism covers match
  data; playback clock/session state is not yet shareable).
- **No authentication; CORS is open.** Appropriate for a hackathon, not for
  enterprise — noted, not hidden.
- **The frontend's API base is a build-time variable** (`NEXT_PUBLIC_API_URL`).
  Set it to `/api` and the same domain's proxy serves both halves (how the live
  demo runs); leave it unset and it defaults to `http://localhost:8000` for
  local dev.
- **No Foundry in this dev environment.** The Foundry/MAF live path is fully
  implemented and tested (including a dead-endpoint fallback test), but runs
  on the deterministic path here.

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
- Scout + Analyst (Chalk) agents with evidence citations — Chalk's reasoning on Microsoft Agent Framework when Foundry is live
- Commentator (Booth) agent (timed broadcast NL, Foundry-narrated) + Director (shared-state blackboard, failure recovery)
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

Cloud: API to ACA (`azure/deploy.sh`); Booth staged as a Foundry hosted agent
definition; span tracing for every agent call. Then demo video (<2 min,
scripted) + README pitch + submit.

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
├── pyproject.toml
├── Dockerfile            # ACA image
├── docs/
│   ├── strategy.md       # Build plan
│   ├── critique.md       # Research-backed tech-stack critique
│   ├── design-vision.md  # v2: pitch-as-blackboard design language + "The Verdict" demo film
│   └── demo-runbook.md   # Frame-by-frame demo choreography
├── azure/
│   ├── panna-aca.bicep   # Self-contained ACA (httpConcurrency, probe, @secure() secret)
│   └── deploy.sh         # build → ACR → deploy → endpoint
├── foundry-config/
│   └── booth-agent.yaml  # Booth staged as a Foundry hosted agent
├── src/
│   ├── events/           # Synthetic generator + canonical event frame
│   ├── agents/
│   │   ├── scout.py      # "Numbers" — event detection + key moment flagging
│   │   ├── analyst.py    # "Chalk" — deterministic tactical insights (evidence-cited)
│   │   ├── commentator.py # "Booth" — timed broadcast commentary
│   │   ├── director.py   # shared-state blackboard, failure recovery
│   │   └── recap.py      # post-match recap
│   ├── foundry/          # Foundry client, MAF reasoning loop, narrative, tracing
│   ├── models/           # xG, PPDA, formation, influence, momentum
│   ├── api/              # FastAPI (REST, SSE replay, playback, share)
│   ├── mcp_server.py     # MCP server — the match toolkit for any MCP client
│   └── cli.py
├── frontend/             # Next.js — the pitch-as-blackboard interface (Dockerized)
└── tests/                # pytest: pipeline, stream, agentic, MAF, MCP, share
```

## Running locally

```bash
# Backend (FastAPI)
pip install fastapi uvicorn pydantic httpx openai "agent-framework>=1.23"
make backend          # http://localhost:8000  (docs at /docs)

# Frontend (Next.js)
cd frontend && npm install && npm run dev   # http://localhost:3000

# Full pipeline CLI
make run-pipeline

# Tests / lint (backend + frontend)
make test
make lint
```

Without Foundry credentials everything runs deterministically offline. To
turn on the live Foundry/MAF path, set (see `.env.example`):
`FOUNDRY_ENDPOINT`, `FOUNDRY_API_KEY`, `FOUNDRY_DEPLOYMENT` (default
`gpt-5.4`), optionally `FOUNDRY_API_VERSION` and `FRONTEND_ORIGIN` (where the
share poster's replay link points).

## Links

- Challenge: https://developer.microsoft.com/en-us/reactor/series/S-1709/
- Rules: https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md
- Synthetic data: https://github.com/microsoft/insidethegamehackathon
