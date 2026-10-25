# Panna — Optimization Strategy

## Current status

- [ ] Synthetic event generator (passes, shots, tackles, possession, etc.)
- [ ] Scout agent (event detection + key moment flagging)
- [ ] Analyst agent (tactical insights with evidence citations)
- [ ] Commentator agent (natural language from Scout + Analyst)
- [ ] Director agent (orchestration + failure recovery)
- [ ] Microsoft Foundry integration (Azure OpenAI)
- [ ] Azure Container Apps deployment
- [ ] Demo video (2 min)
- [ ] Submit

## The 4-agent pipeline

### Scout (event detection)
- Watches the synthetic event stream
- Flags key moments: shots, tackles, possession shifts, formation changes, set pieces
- Output: structured event markers with timestamps and evidence citations

### Analyst (tactical insights)
- Computes tactical insights from Scout output:
  - xG (expected goals) per shot
  - Formation effectiveness (how well the formation is working)
  - Pressing intensity (how hard the team is pressing)
  - Player influence (who's affecting the game most)
  - Momentum shifts (when did the game change direction)
- Output: statistical insights with evidence citations (which events led to this)

### Commentator (natural language)
- Takes Scout + Analyst output
- Generates broadcast-style commentary
- Natural language, timed to match the event stream
- Tone: professional broadcast analyst

### Director (orchestration)
- Orchestrates all three agents
- Decides what to surface and when
- Handles failure recovery (if one agent fails, the others continue)
- Manages shared state between agents
- Prioritizes insights for broadcast

## Synthetic data format

Events are JSON objects with:
```json
{
  "minute": 23,
  "second": 45,
  "type": "pass",
  "player": "Player A",
  "team": "Home",
  "position": {"x": 45.2, "y": 30.1},
  "target": {"x": 60.5, "y": 25.3},
  "outcome": "success",
  "metadata": {"pass_type": "through", "distance": 15.3}
}
```

Event types:
- `pass` (short, long, through, cross, back)
- `shot` (on_target, off_target, blocked, goal)
- `tackle` (successful, unsuccessful)
- `interception`
- `foul` (yellow, red, no card)
- `possession_change`
- `formation_change`
- `substitution`
- `set_piece` (corner, free_kick, penalty, throw_in)
- `goal` (with assist, type)

## Microsoft Foundry integration

- Use Azure OpenAI (GPT-4o) for agent reasoning
- Foundry orchestrates the 4-agent pipeline
- Each agent is a Foundry deployment with its own system prompt
- Shared state managed through Foundry's context

## Azure deployment

- **Azure Container Apps** for the API (event-driven, serverless)
- **Azure Event Hubs** for synthetic event stream ingestion
- **Azure Functions** for individual agent processing
- **Azure AI Search** for RAG (historical match context)

## Daily iteration plan

- **Day 1 (Oct 25-26):**
  - Morning: Synthetic event generator + Scout agent
  - Midday: Analyst agent + evidence citations
  - Afternoon: Commentator agent + basic Director
  - Evening: Test end-to-end, fix bugs

- **Day 2 (Oct 26-27):**
  - Morning: Microsoft Foundry integration
  - Midday: Azure deployment
  - Afternoon: Demo video + submit
  - Evening: Buffer for fixes

## What to cut if time is short

1. Personalized fan experience (nice-to-have)
2. 3D broadcast (SportWarren already has this)
3. Azure Event Hubs (use simpler polling)
4. Azure AI Search (skip RAG, use simpler context)

## What we're NOT doing

- Not claiming real Premier League data (synthetic only)
- Not claiming SportWarren integration (separate project, merge later)
- Not claiming enterprise readiness (demo only)
- Not claiming mainnet deployment (test/demo only)
