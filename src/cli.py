"""CLI: generate a match and run the full pipeline.

Subcommands:
  ``run``      (default) — generate a match and print the pipeline output
  ``redteam``  — plant known-false lines, measure the Verifier's catch rate,
                 and write reports/verifier-redteam.md
  ``evaluate`` — detection coverage + verification summary scorecard
"""

from __future__ import annotations

import argparse
import json

from src.agents.director import DirectorAgent
from src.agents.recap import RecapAgent
from src.events.generator import MatchConfig, SyntheticMatchGenerator


def _run(args: argparse.Namespace) -> None:
    cfg = MatchConfig(match_id=args.match_id, seed=args.seed)
    events = SyntheticMatchGenerator(cfg).generate()
    print(f"Generated {len(events)} events")

    director = DirectorAgent()
    result = director.run({"events": events})
    print("\n=== HEALTH ===")
    print(json.dumps(result["health"], indent=2))
    print("\n=== VERIFICATION ===")
    print(json.dumps(result.get("verification", {}), indent=2))
    print("\n=== INSIGHTS ===")
    for ins in result["insights"]:
        v = ins.verification.status if ins.verification else "?"
        print(f"  [{ins.type}] {ins.claim} (conf={ins.confidence}, verdict={v})")
    print("\n=== COMMENTARY (first 5) ===")
    for c in (result["commentary"] or [])[:5]:
        v = c.verification.status if c.verification else "?"
        print(f"  {c.minute}' {c.text} [{v}]")
    print("\n=== RECAP ===")
    print(RecapAgent().run({"insights": result["insights"], "key_moments": result["key_moments"]}))


def _redteam(args: argparse.Namespace) -> None:
    from src.redteam import run_redteam, write_report

    report = run_redteam(seed=args.seed)
    print(json.dumps(report, indent=2))
    path = write_report(report)
    print(f"\nReport written to {path}")


def _evaluate(args: argparse.Namespace) -> None:
    """Scorecard: detection coverage + verification + determinism."""
    events = SyntheticMatchGenerator(MatchConfig(match_id=args.match_id, seed=args.seed)).generate()
    result = DirectorAgent().run({"events": events})

    goals = [e for e in events if e.type.value == "goal"]
    detected = {km.event_id for km in result["key_moments"]}
    goals_flagged = sum(1 for g in goals if g.id in detected)
    verdicts = list(result.get("verdicts", {}).values())

    # determinism: same seed → same event ledger
    cfg2 = MatchConfig(match_id=args.match_id, seed=args.seed)
    events2 = SyntheticMatchGenerator(cfg2).generate()
    deterministic = [e.id for e in events] == [e.id for e in events2]

    print(
        json.dumps(
            {
                "seed": args.seed,
                "events": len(events),
                "goal_detection": f"{goals_flagged}/{len(goals)}",
                "verifier": result.get("verification", {}),
                "verdict_statuses": {
                    s: sum(1 for v in verdicts if v.status == s)
                    for s in ("verified", "repaired", "rejected")
                },
                "deterministic_replay": deterministic,
                "commentary_source": result.get("commentary_source"),
                "reasoning_source": result.get("reasoning_source"),
            },
            indent=2,
        )
    )


def main() -> None:
    p = argparse.ArgumentParser(prog="panna-run")
    p.add_argument("--match-id", default="match_001")
    p.add_argument("--seed", type=int, default=42)
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("run")
    rt = sub.add_parser("redteam")
    rt.add_argument("--seed", type=int, default=137)
    sub.add_parser("evaluate")
    args = p.parse_args()

    {"redteam": _redteam, "evaluate": _evaluate}.get(args.cmd, _run)(args)


if __name__ == "__main__":
    main()
