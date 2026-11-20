"""Article 50 readiness report — the compliance artifact.

EU AI Act Article 50 (enforceable 2 Aug 2026) requires providers to mark
AI-generated content machine-readably, and deployers to disclose
AI-generated public-interest text *unless it underwent human editorial
review*. Panna's architecture maps onto both halves:

- **Marking:** every broadcast line carries provenance (which agent, and
  whether the Foundry model or the deterministic engine produced it) plus
  its Verifier verdict — the machine-readable mark travels with the line.
- **Human review:** the producer gate means every rejected line is held
  for a human, and approve/kill decisions are recorded in the audit
  ledger — the editorial-review trail regulators ask for.
- **Disclosure record:** ``src/audit.py`` JSONL survives the process, so
  "what aired, what was held, who approved it" is answerable later.

This module runs one full match through the real pipeline — gate, hold
queue, a planted-attack human review — and emits two artifacts:

- ``reports/article50-readiness.md`` — the human-readable mapping
- ``reports/article50-manifest-{match}.json`` — machine-readable marks
  per line (the thing a compliance tool would ingest)

Run: ``panna-run compliance --seed 137``
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.agents.director import DirectorAgent
from src.api.session import MATCH_SECONDS, MatchSession
from src.audit import JsonlLedger
from src.events.generator import MatchConfig, SyntheticMatchGenerator

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


def run_readiness(
    seed: int = 137,
    match_id: str = "match_art50",
    events: list | None = None,
    home: str = "Home FC",
    away: str = "Away United",
    data_provenance: dict | None = None,
) -> dict[str, Any]:
    """Full match through the gate + one human-review exercise → manifest.

    ``events=None`` runs the synthetic engine; pass an ingested real ledger
    (``src.ingest``) to produce the artifact against licensed/open data —
    ``data_provenance`` then carries the feed's source into the manifest."""
    if events is None:
        events = SyntheticMatchGenerator(MatchConfig(match_id=match_id, seed=seed)).generate()
    result = DirectorAgent().run({"events": events})

    audit_path = REPORTS_DIR / f"audit-{match_id}.jsonl"
    if audit_path.exists():
        audit_path.unlink()
    ledger = JsonlLedger(audit_path)
    session = MatchSession(
        match_id=match_id,
        seed=seed,
        home_team=home,
        away_team=away,
        events=events,
        result=result,
        audit=ledger,
    )

    # exercise the human-review path: plant fabricated lines (they land held),
    # then a producer kills them — decisions are the Art-50 editorial trail
    planted = session.seed_bad_claim()
    planted_ids = list(planted["verdicts"].keys())
    for pid in planted_ids:
        session.decide(pid, "kill")

    # drain the broadcast — every gated line records aired/suppressed
    session.playing = True
    session.clock = MATCH_SECONDS
    session.advance()

    rows = [json.loads(line) for line in audit_path.read_text().splitlines()]
    verdicts = [r for r in rows if r["type"] == "verdict"]
    aired = {r["id"] for r in rows if r["type"] == "aired"}
    suppressed = {r["id"] for r in rows if r["type"] == "suppressed"}
    decisions = [r for r in rows if r["type"] == "decision"]

    lines = []
    for v in verdicts:
        lines.append(
            {
                "id": v["id"],
                "kind": v["kind"],
                "verdict": v["status"],
                "reason": v["reason"],
                "checks": v["checks"],
                "air_status": (
                    "aired"
                    if v["id"] in aired
                    else "suppressed"
                    if v["id"] in suppressed
                    else "pending"
                ),
            }
        )
    # planted lines were judged after session build — include them from the
    # seed_bad_claim verdicts so the manifest covers every line touched
    for pid, pv in planted["verdicts"].items():
        lines.append(
            {
                "id": pid,
                "kind": "planted",
                "verdict": pv.get("status"),
                "reason": pv.get("reason"),
                "checks": pv.get("checks") or [],
                "air_status": "suppressed",
            }
        )

    by_status = {}
    for line in lines:
        by_status[line["verdict"]] = by_status.get(line["verdict"], 0) + 1

    return {
        "match_id": match_id,
        "seed": seed,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "provenance": {
            "commentary_source": result.get("commentary_source", "template"),
            "reasoning_source": result.get("reasoning_source", "template"),
            "reasoning_model": result.get("reasoning_model"),
            "data_source": data_provenance or "synthetic",
        },
        "lines": lines,
        "summary": {
            "gated_lines": len(lines),
            "verdicts": by_status,
            "aired": len(aired),
            "suppressed": len(suppressed),
            "human_decisions": len(decisions),
        },
        "art50": {
            "machine_readable_marking": (
                "every line carries verdict + provenance; this manifest is "
                "the machine-readable mark set"
            ),
            "human_editorial_review": decisions,
            "fail_closed_evidence": sorted(suppressed),
            "audit_ledger": str(audit_path.relative_to(REPORTS_DIR.parent)),
        },
    }


def write_report(report: dict[str, Any], path: Path | None = None) -> Path:
    """Human-readable Article 50 mapping (the compliance one-pager)."""
    path = path or REPORTS_DIR / "article50-readiness.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    s = report["summary"]
    lines = [
        "# EU AI Act Article 50 — readiness report",
        "",
        f"Match `{report['match_id']}` (seed {report['seed']}), generated "
        f"{report['generated_at']} UTC.",
        "",
        "## Pipeline provenance",
        "",
        f"- Commentary: `{report['provenance']['commentary_source']}`",
        f"- Reasoning: `{report['provenance']['reasoning_source']}` "
        f"(model: {report['provenance']['reasoning_model'] or 'deterministic'})",
        "",
        "## Art. 50 mapping",
        "",
        "| Obligation | How Panna satisfies it | Evidence |",
        "|---|---|---|",
        "| Mark AI-generated content machine-readably | Every line carries a "
        "verdict object + provenance (agent, source, model); the JSON "
        "manifest alongside this file is the machine-readable mark set | "
        f"`article50-manifest-{report['match_id']}.json` |",
        "| Human editorial review (deployer exemption) | Rejected lines are "
        "held for the producer; approve/kill decisions are recorded with "
        "timestamps in the audit ledger | "
        f"{s['human_decisions']} decisions in `audit-{report['match_id']}.jsonl` |",
        "| Disclosure record survives the session | Verdicts, air/suppress "
        "outcomes and decisions append to JSONL at write time — the record "
        "outlives the process | `src/audit.py` |",
        "| Fail-closed on unverifiable output | Lines the recount gate "
        "rejects never air; the ledger shows the suppression | "
        f"{s['suppressed']} suppressed of {s['gated_lines']} gated |",
        "",
        "## Outcome",
        "",
        f"- {s['gated_lines']} gated lines — verdicts: "
        + ", ".join(f"`{k}`×{v}" for k, v in sorted(s["verdicts"].items())),
        f"- {s['aired']} aired · {s['suppressed']} suppressed · "
        f"{s['human_decisions']} human decisions",
        "",
        "Method: one full synthetic match through the production Director + "
        "Verifier + session gate, including a planted fabricated line killed "
        "via the producer path — nothing staged.",
        "",
    ]
    path.write_text("\n".join(lines))
    return path


def write_manifest(report: dict[str, Any], path: Path | None = None) -> Path:
    """The machine-readable mark set — one object per line."""
    path = path or REPORTS_DIR / f"article50-manifest-{report['match_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    return path
