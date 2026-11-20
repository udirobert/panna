# EU AI Act Article 50 — readiness report

Match `match_art50` (seed 137), generated 2026-11-20T15:10:38+00:00 UTC.

## Pipeline provenance

- Commentary: `template`
- Reasoning: `template` (model: deterministic)

## Art. 50 mapping

| Obligation | How Panna satisfies it | Evidence |
|---|---|---|
| Mark AI-generated content machine-readably | Every line carries a verdict object + provenance (agent, source, model); the JSON manifest alongside this file is the machine-readable mark set | `article50-manifest-match_art50.json` |
| Human editorial review (deployer exemption) | Rejected lines are held for the producer; approve/kill decisions are recorded with timestamps in the audit ledger | 2 decisions in `audit-match_art50.jsonl` |
| Disclosure record survives the session | Verdicts, air/suppress outcomes and decisions append to JSONL at write time — the record outlives the process | `src/audit.py` |
| Fail-closed on unverifiable output | Lines the recount gate rejects never air; the ledger shows the suppression | 2 suppressed of 45 gated |

## Outcome

- 45 gated lines — verdicts: `rejected`×2, `verified`×43
- 43 aired · 2 suppressed · 2 human decisions

Method: one full synthetic match through the production Director + Verifier + session gate, including a planted fabricated line killed via the producer path — nothing staged.
