# Panna Design Vision v2 — The Pitch Is the Blackboard

> North star: **there is no dashboard beside the match.** The match surface *is* the
> agents' shared workspace. Everything the intelligence thinks, it thinks **on the
> pitch** — as chalk, as glow, as swarm movement.
>
> The demo is a forensic film, **"The Verdict"**: Panna cross-examines a lazy
> full-time take and proves its case with annotated evidence on the board.

Evolved 2026-10-25 from v1 (broadcast-dashboard vision) after research into novel
agent-coordination patterns. v1's card grid, named-role panels, and sizzle-reel
opener are explicitly retired: judges have seen hundreds of "four agents light up"
demos, and cards are the most common UI primitive in agent tooling.

---

## 1. Coordination architecture (the actual differentiator)

### Pattern: Blackboard + stigmergy + quorum sensing

Research grounding:
- **Blackboard systems** — specialists watch a shared workspace and opportunistically
  contribute when their expertise becomes relevant; no single planner owns the flow.
  Built for exactly this problem class: diagnosis and synthesis under uncertainty.
  (en.wikipedia.org/wiki/Blackboard_system; tianpan.co "The Blackboard Is Back")
- **Stigmergy** — coordination through traces left in a shared environment (ant
  pheromone trails); later agents react to earlier traces rather than messaging.
  (en.wikipedia.org/wiki/Stigmergy; gc-bs.org)
- **Quorum sensing** — commit only after enough independent detectors reach the same
  conclusion, honeybee-nest style; suited to high-stakes factual claims.
- **Boids/flocking** — Craig Reynolds' distributed behavioral model; browser ant-colony
  sims prove pheromone-style emergence is visually legible in canvas.
  (red3d.com/cwr/boids; starlighttools.org ant-colony sim)

### Mapping to Panna

The four backend agents (already built in `src/agents/`) are re-presented as **three
actors and one place**. The backend modules stay; the Director still orchestrates
under the hood (shared state, staggered reveals, failure recovery) and Chalk's
reasoning runs on Microsoft Agent Framework when Foundry is live. The
*presentation* is decentralized:

| Backend module | Presentation | Nature |
|---|---|---|
| `scout.py` | **Numbers** — the swarm | Many lightweight detectors as flocking particles, not one persona. Drifts across the event stream; converges where signal accumulates. |
| `analyst.py` | **Chalk** — the specialists | Pressing, shape, xG, momentum operate as blackboard knowledge sources: they never message each other, they watch the board and write when relevant. Chalk turns Numbers into proof. |
| `commentator.py` | **Booth** | Narration emerging as telestrated chalk + ticker-band text. The voice you'd hear on air. |
| `director.py` | **the Pitch** | Coordination is a *place*, not a boss. The shared board is the orchestration artifact. |

The pipeline reads like broadcast folklore: **Numbers see it, Chalk proves it, Booth says it.**
Football-culture naming chosen over functional names (Vision/Pulse/Voice) — decided 2026-10-25.

**Quorum = key moment.** When enough swarm particles converge on a detection, it
solidifies into a chalk mark. That hardening animation *is* a KeyMoment.

**Stigmergy = evidence.** Chalk marks are traces: later specialists react to earlier
marks. An insight's `evidence` list renders as visible trails back to the marks that
provoked it.

**Failure recovery = emergence, not status lights.** A specialist cluster goes dark;
its half-drawn chalk stays on the board; peer particles converge on the orphaned
traces and finish the annotation. No amber card, no status pill — the system visibly
heals through the environment.

### Naming — decided
**Numbers / Chalk / Booth** + the Pitch (football-culture identity). Backend module
names (scout/analyst/commentator/director) unchanged.

---

## 2. Card-free visual vocabulary

Five primitives replace the card grid entirely:

1. **Chalk (telestration)** — annotations drawn live onto the pitch surface: circles,
   arrows, freehand-style zones. Telestration is the native visual language of sports
   explanation (Madden used it from Super Bowl XVI onward). SVG stroke-path draw-on
   animation. Chalk marks persist and accumulate — by full time the pitch carries the
   match's entire argument. (proplayvision.com, en.wikipedia.org/wiki/Telestrator)

2. **The swarm** — boid particles in team colors on one canvas layer: drift, converge,
   form quorum rings that harden into chalk. The multi-agent judging criterion made
   visible as emergent behavior rather than a topology diagram.

3. **Pitch-control glow** — Fernández/Bornn-style dominance field under the action:
   a continuous home/away control surface that breathes with possession. Replaces
   momentum bar charts with something spatial and sport-native.
   (getgoalsideanalytics.com pitch-control history; Spiideo Perform ships this for coaches)

4. **The ticker band** — commentary as a Ceefax/teletext-style strip along the bottom
   edge: minute stamps, tone-colored text blocks, dense and instant-broadcast.
   Teletext revival is proven football culture (Telescore app, Ceefax merch).

5. **The score bug** — the single persistent chrome element (crest, score, clock,
   LIVE state). Broadcast convention, not a card. Modern scorebug design is trending
   minimal: "let the live image breathe, information appears only when it is useful."
   (sportsvideo.org, June 2026)

**Evidence Spotlight (v1) survives, re-skinned:** hover/click an insight's evidence
→ the board dims, cited events glow gold, chalk lines draw themselves from claim to
event. Telestration replaces tooltip cards.

**Insights live on the board**, not in a tray: each is a chalk mark with a confidence
dial ring around it. Expanding one opens a *lens* onto the board region, not a modal card.

## 3. Design language

- Fluent 2 acrylic adapted to deep pitch-green-black (`#0A1210` range), stadium-light
  vignette. Translucent layers without boxes (2026 spatial-UI trend: depth and glow,
  not bordered containers).
- Accents: **gold** = AI claims/evidence, **cyan** (home) vs **amber** (away) = team
  identity everywhere, **green/red** reserved for specialist-cluster integrity.
- Condensed display face for clock/score/headlines; Segoe UI Variable for body.
- Fictional clubs, generated crests — the synthetic-data rule as brand feature:
  "every match, a new league."
- Respect `prefers-reduced-motion`.

## 4. Live transport

SSE replay via FastAPI `StreamingResponse` → browser `EventSource`. New endpoint:
`GET /matches/{id}/stream` emitting `event`, `detection` (quorum), `insight`,
`commentary`, `agent_status`. Match replays at ~60× so a full match unfolds in ~90 s.
Requirements beyond forward replay (for The Verdict):

- **reverse playback** — scrub/rewind mode (chalk un-draws, swarm scatters)
- **freeze-frame** — pause clock, allow layer peeling on a still
- **failure injection** — scriptable endpoint to darken a specialist cluster at a
  director-chosen beat

## 5. The Verdict — the 2-minute demo film

Structure: forensic. Open at full time with a pundit's lazy verdict; spend the film
cross-examining it; close by printing the annotated board as the recap artifact.
Under 90 words of on-screen text, no voiceover. The agents are never introduced with
role cards — their roles emerge from what they do to the board.

| Time | Beat | What the camera shows |
|---|---|---|
| 0:00–0:10 | The crime scene | Full time. Frozen board. Verdict quote slams in: *"BROOKFIELD WANTED IT MORE."* Cursor drags it onto the board to open a case. |
| 0:10–0:35 | Rewinding the tape | Clock spools back; chalk un-draws; swarm scatters into drift. Hard stop on a frozen midfield frame. Layers peel: pitch-control glow, pass vectors, xG cone. Booth telestrates: *"Everyone saw the tackle. Panna saw the trap."* First Evidence Spotlight. |
| 0:35–0:55 | Cross-examination | Three exhibits, each one chalk pass over a frozen frame, each cited by Evidence Spotlight: (1) momentum — the "losing" side dominated 28 minutes; (2) the 54' shape change the pundit missed, board reconfiguring live; (3) the equalizer that wasn't — 0.31 xG chance, shot ring expanding and dying on the keeper. |
| 0:55–1:15 | Same evidence, three witnesses | One passage replayed three ways: tactical lens (control glow + shape chalk), attack lens (shot rings + xG race), story lens (ticker + celebrations). One board, three truths. The personalization hook. |
| 1:15–1:40 | The plot twist | Specialist cluster flickers dark mid-investigation. Its half-drawn chalk stays. Peer particles converge on the traces, finish the annotation, integrity restored. Stigmergy on camera — the failure-recovery criterion delivered as drama. |
| 1:40–1:55 | Verdict | The fully annotated board assembles into the recap: *"OVERTURNED — out-pressed for 28 minutes, rescued by a goalkeeper."* Every mark cites its evidence chain. A shareable broadcast artifact. |
| 1:55–2:00 | The invitation | Board clears. Fresh fixture. Blinking seed number, regenerated on screen: a *new* match's first event drops as credits roll (Azure / Foundry / MAF small print). *"Every match leaves a verdict. Cross-examine yours."* |

Why this wins: the structure *is* the pitch — explainable intelligence dramatized as
forensics; multi-agent collaboration shown as emergence; failure recovery as a plot
twist; the villain (lazy punditry) is culturally resonant; the usage driver is baked
in — every future match is an open case.

### Usage flywheel the film plants
1. **Generative, never content-starved** — infinite seeds, regenerated on air.
2. **Personalized** — one keystroke changes the film (lenses).
3. **Revealing** — the AI finds what humans missed (cross-examination).
4. **Shareable** — the annotated board prints as the recap artifact.
5. **Second screen** — completes the broadcast, doesn't replace it.

## 6. Tech map

| Need | Choice | Rationale |
|---|---|---|
| Pitch + chalk | Hand-rolled SVG pitch, stroke-path telestration with draw-on animation | mplsoccer/StatsBomb coordinates (0–120 × 0–80) already in `src/events/schema.py` |
| Swarm | One canvas layer, ~40–80 boids with flocking + quorum-converge states (~150-line known implementation) | red3d.com/cwr/boids; timebox to one afternoon |
| Pitch control glow | Simplified control surface from event positions + possession metadata | Fernández/Bornn pitch control; approximate, not simulate |
| Momentum/xG race | SVG area charts, BBC-style per-minute max-danger encoding | bbc.com Match Momentum |
| Ticker | CSS strip, Ceefax palette accents, tone-colored blocks | teletext revival precedents |
| Animation | **Motion** (ex-Framer Motion) for SVG/chalk/CSS; canvas swarm self-animated | motion.dev; React dashboard consensus |
| Live transport | SSE replay + rewind + freeze + failure injection | FastAPI StreamingResponse |
| Sound | Broadcast ambience bed, insight chime, crowd swell at goal | sound design is half the film |

## 7. Build order (Day 2) — build the shots, not the screens

Every item maps to a beat in §5. Nothing is built that the camera never sees.

1. SSE stream + replay clock + rewind/freeze/injection controls (beats 2–6)
2. Pitch SVG + chalk telestration system + Evidence Spotlight (beats 2–3, core ask)
3. Swarm canvas: drift, converge, quorum-harden (beats 1–2, 6)
4. Pitch-control glow + momentum/xG SVG (beats 3, 5)
5. Ticker band + score bug + lens switching (beats 2, 5)
6. Specialist failure/recovery choreography, rehearsed (beat 6)
7. Recap = annotated-board print layout (beat 7)
8. Seed regeneration on air + invitation screen (beats 1, 8)
9. Sound pass + title cards naming rubric criteria

### Scope — decided
**Full boids swarm** (~40–80 particles, flocking + quorum hardening) for maximum
differentiation. Emergency fallback only if Day 2 slips badly: swarm degrades to
15–20 particles with simple convergence easing (no full flocking). Chalk + Evidence
Spotlight are never cut — they carry explainability, the hackathon's core ask.

## 8. What v1 got wrong (kept as lessons)

- "Four agents light up" openers are the most saturated trope in agent demos.
- Cards read as generic tooling, not broadcast; the industry trend itself is
  minimal chrome ("let the live image breathe").
- A dashboard next to the match splits attention; putting intelligence *on* the match
  is both truer to the domain and rarer in the field.
