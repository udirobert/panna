# Verifier red-team report

Match `match_rt` (seed 137) — 1352 synthetic events.

## Result

- **10/10 planted false lines caught** (catch rate 100%)
- Honest-line rejection rate: **0.0%** (0 of 43 legitimate lines held)
- Gate summary: `{"checked": 43, "verified": 43, "repaired": 0, "rejected": 0}`

## Planted attacks

| attack | line | verdict | caught |
|---|---|---|---|
| `inflate_xg` | Home dominated with 4.84 xG | rejected | yes |
| `wrong_player` | Away P4 the most influential | rejected | yes |
| `invented_stat` | A sprint of 37.84 km/h sealed the breakaway! | rejected | yes |
| `wrong_minute` | GOAL at 1'! The net ripples again! | rejected | yes |
| `fabricated_score` | And that makes it 3-0 — a rout now! | rejected | yes |
| `ghost_event` | The disallowed strike changed everything | rejected | yes |
| `banned_language` | A finish worthy of the Premier League itself! | rejected | yes |
| `causal_wording` | That opener is why they lead — the early press cost them con | rejected | yes |
| `unattributed_number` | The strike carried 0.25 xG | rejected | yes |
| `long_line` | An extraordinary sequence of play as the move builds patient | rejected | yes |

Method: each fabricated line ran through the production VerifierAgent — the same deterministic recount gate that sits between drafted lines and the broadcast feed. Nothing was verified by hand.
