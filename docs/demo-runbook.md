# "The Verdict" — Demo Film Runbook

> Records the 2-minute demo exactly. One operator, one take, ~3 retakes allowed.
> Script: <90 words on screen, no voiceover (audio = ambience bed + goal swell + insight chime, added in edit).
> Target duration: 2:00 max (submission limit).

## Pre-flight

```bash
make backend            # http://localhost:8000
make frontend           # http://localhost:3000
```

- Browser at 1440×900, 100% zoom, dark mode. Record at 2× and downscale in edit.
- Pick a seed and verify it by hand first (see below) — the take must be a match
  with **≥2 goals and a clear 28-minute momentum swing** for the "cross-exam" beats.
  Good seeds are match-specific; if in doubt, roll 3, scrub each to full time at 300×,
  and keep the best. Write the chosen seed here: `SEED = ____`.
- Close all tabs except the app. Kill notifications.

## Beats

| # | Time | Screen | Action |
|---|---|---|---|
| 1 | 0:00 | The pitch, frozen at FT | Open the app, generate `SEED`, let it play at 300× until full time, then seek back to 0:00 (⏪ repeatedly) and **freeze**. Verdict card (title card, added in edit): *"BROOKFIELD WANTED IT MORE — every pundit, probably."* |
| 2 | 0:10 | Rewind | Hit ⏭ to advance 1 minute at a time; the board un-draws (chalk, rings, swarm). Hold on a frozen midfield frame. Overlay: *"Everyone saw the tackle. Panna saw the trap."* |
| 3 | 0:22 | Evidence spotlight | Click an insight strip on the right (pick the one with the most evidence chips). The board dims; cited events light gold with numbered rings + attribution lines. Do it twice fast with different insight types. |
| 4 | 0:35 | Cross-examination | Three exhibits, one chalk pass each (all real clicks): ① switch to **TACTICAL** lens → control glow + shape read; ② switch to **ATTACK** → shot rings + xG race in the momentum chart; ③ point the cursor at the 0.31-xG saved chance (largest shot ring that isn't a goal). |
| 5 | 0:55 | Three witnesses | Same passage, three lenses in 15 s: TACTICAL → ATTACK → STORY (ticker + celebrations only). Overlay: *"One match, three broadcasts. Your lens."* |
| 6 | 1:15 | The plot twist | Click **CHALK** in the agent rail → it goes dark (blinking red dot, "CHALK DARK — TRACES PRESERVED" appears over the pitch). Let 2 match-minutes pass at 60× (the board keeps moving). Click CHALK again to recover → buffered findings flush in marked "↺ recovered by peers". Overlay: *"Evidence preserved. Investigation continues."* |
| 7 | 1:40 | Goal | Seek to the minute just before the biggest goal. Play at 60×. Goal burst + flash + score bug flip + ticker. Let it breathe 3 s. |
| 8 | 1:52 | Verdict | Seek to full time (⏭ to end). The Verdict panel assembles: headline, recap, exhibits E1–E4. Overlay: *"OVERTURNED — out-pressed for 28 minutes, rescued by a goalkeeper."* |
| 9 | 1:58 | Invitation | Click **CROSS-EXAMINE YOURS** → confirm → a *new* match generates on air (seed changes in the header, board resets). Hold as the first events land. Small print: Azure · Foundry · MAF. Final card: *"Every match leaves a verdict. Cross-examine yours."* |

## Editing checklist

- [ ] Title cards name the rubric criteria as they appear: **MULTI-AGENT ORCHESTRATION** (beat 6), **EXPLAINABILITY** (beat 3), **FAILURE RECOVERY** (beat 6), **AZURE / FOUNDRY** (beat 9)
- [ ] Insight chime on each spotlight (beat 3); crowd swell on goal (beat 7)
- [ ] Cut to the clock tick, not the mouse click
- [ ] Under 2:00 with credits; upload to YouTube (public) — submission needs a public URL

## Fallbacks if a beat misbehaves live

| Failure | Fallback |
|---|---|
| Match has no clean momentum swing | Regenerate with a different seed before recording (pre-flight step) |
| A spotlight cites an event off-screen (pass out of view) | Pick a different insight strip; every insight's evidence is on-board by construction |
| Recovery flush feels slow | Keep the match **playing** while CHALK is dark — buffered findings flush on recover (the clock must pass them). Do not fail/recover while frozen at full time. |
| SSE drops (network hiccup) | The client resyncs automatically from the last snapshot; just keep playing |
