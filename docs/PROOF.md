# PROOF — how trust works in Panna

The question every judge eventually asks of an AI broadcast: *what stops a
made-up stat reaching the screen?* Panna's answer is structural, not
rhetorical.

## The gate is never the author

```
events (code) ──► Scout ──► Analyst/Chalk (MAF tools) ──► Booth ──► GATE ──► air
                                                                │
                                                          ┌─────▼──────┐
                                                          │  Verifier  │  deterministic recount
                                                          └─────┬──────┘
                                                  rejected ────►│ HOLD ──► producer approve / kill
```

The Verifier (`src/agents/verifier.py`) is plain Python. It did not write any
line it judges. For every broadcast item it:

1. **Grounds evidence** — every cited event id must exist in the ledger.
2. **Recounts typed stats** — for `xg_total`, `pressing_intensity`,
   `formation_effectiveness`, `player_influence`, `momentum_shift` it reruns
   the same `src/models` functions on the raw events and compares.
3. **Grounds every written number** — a float in the text is only legal if an
   engine-recounted value rounds to it at the precision it was written
   (so `8.4` ≈ a real `8.42`, but `37.84 km/h` fails).
4. **Grounds minute refs** — `N'` must be a minute where the claimed thing
   happened; a goal line needs a real goal at `N'±1`.
5. **Grounds scorelines** — `N-M` must equal the running score at the line's
   minute.
6. **Grounds attribution** — a "most influential player" claim must name the
   player the recount names.

## Three verdicts

| Verdict | Meaning | What airs |
|---|---|---|
| `verified` | every checkable number recounted | the line, with a `✓ verified` chip |
| `repaired` | a wrong number, mechanically fixable (e.g. xG total) | the **corrected** line, flagged `✎ repaired`, original kept in `repair_of` |
| `rejected` | ungrounded or unfixable | **nothing** — the line is held for the producer |

The gate fails closed: when in doubt, the line waits for a human.

## The producer is real

`GET /producer/{match}/board` lists every line with its verdict and air
status; `POST /producer/{match}/decide` approves or kills. The frontend
console (`/producer?match=…`) shows the hold queue, the per-check "why?",
and the one-click red-team seeder.

## The demo is the test

- `POST /stream/playback/{match}` `{action: "seed_bad_claim"}` injects a
  fabricated scoreline + invented stat into the live timeline; the gate
  rejects both and they surface in the hold queue.
- `panna-run redteam` plants one line per attack class (inflated xG, wrong
  player, invented stat, wrong minute, fabricated score, ghost evidence)
  and publishes the catch rate — see `reports/verifier-redteam.md`.
- The MCP tool `verify_line(match_id, text)` runs the same gate over any
  prose, so an external agent can audit a claim without trusting Panna.

## Measured

From `reports/verifier-redteam.md` (seed 137, 1 656 events):

- **6/6 planted false lines caught** (catch rate 100%)
- **0/43 honest lines rejected** (0% false-positive tax)
- All 43 broadcast items carry verdicts in `result["verdicts"]`

## Honest limits

- Bare integers and ordinals ("his 9th goal") aren't yet bound to checks —
  recorded as unchecked in the verdict rather than silently passed.
- Translation/localization re-verification is implemented in the gate
  design but the localize endpoint itself is staged (see CLAIMS.md).
- The verifier recounts against the synthetic ledger — against real Opta/PL
  feeds the same code runs unchanged, only the event source differs.
