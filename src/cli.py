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
from pathlib import Path

from src.agents.director import DirectorAgent
from src.agents.recap import RecapAgent
from src.events.generator import MatchConfig, SyntheticMatchGenerator


def _run(args: argparse.Namespace) -> None:
    if getattr(args, "real", False):
        real = _resolve_ingest(args)
        if real is None:
            print("no data — statsbomb needs --match-id; sportmonks needs a token")
            return
        events, prov = real.events, real.provenance
        print(
            f"Ingested {len(events)} events — {prov.get('home_team')} v "
            f"{prov.get('away_team')} ({prov['provider']})"
        )
    else:
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


def _compliance(args: argparse.Namespace) -> None:
    from src.compliance import run_readiness, write_manifest, write_report

    real = _resolve_ingest(args) if getattr(args, "real", False) else None
    if real is not None:
        events, prov = real.events, real.provenance
        match_id = str(prov.get("match_id") or prov.get("fixture_id") or "real")
        report = run_readiness(
            match_id=f"{prov['provider']}_{match_id}",
            events=events,
            home=prov.get("home_team") or "Home",
            away=prov.get("away_team") or "Away",
            data_provenance=prov,
        )
        print(
            f"data: {prov['provider']} — {prov.get('home_team')} v {prov.get('away_team')}"
            f" ({prov['events_mapped']} events, {prov['events_skipped']} skipped)"
        )
    else:
        report = run_readiness(seed=args.seed, match_id=args.match_id)
    md = write_report(report)
    manifest = write_manifest(report)
    print(json.dumps(report["summary"], indent=2))
    print(f"\nReport: {md}\nManifest: {manifest}")


def _resolve_ingest(args: argparse.Namespace):
    """Shared provider resolution — returns IngestResult or None."""
    from src.ingest import SportmonksAdapter, StatsBombAdapter

    refresh = getattr(args, "refresh", False)
    if args.provider == "statsbomb":
        adapter = StatsBombAdapter()
        if args.file:
            payload = json.loads(Path(args.file).read_text())
            return adapter.to_events(
                payload.get("events", payload),
                home=args.home or payload.get("home", "Home"),
                away=args.away or payload.get("away", "Away"),
                match_id=str(args.match_id or payload.get("match_id") or "sb_file"),
            )
        if args.match_id:
            return adapter.fetch(
                args.competition_id, args.season_id, int(args.match_id), refresh=refresh
            )
        return None
    adapter = SportmonksAdapter()
    if args.file:
        payload = json.loads(Path(args.file).read_text())
        return adapter.to_events(payload.get("data", payload))
    if args.fixture_id:
        return adapter.fetch(args.fixture_id, refresh=refresh)
    return None


def _add_ingest_args(p: argparse.ArgumentParser, include_match_id: bool = True) -> None:
    p.add_argument("--provider", choices=["statsbomb", "sportmonks"], default="statsbomb")
    p.add_argument("--fixture-id", type=str, default="")
    if include_match_id:
        p.add_argument("--match-id", type=str, default="")
    p.add_argument("--competition-id", type=int, default=43)
    p.add_argument("--season-id", type=int, default=3)
    p.add_argument("--home", type=str, default="")
    p.add_argument("--away", type=str, default="")
    p.add_argument("--file", type=str, default="")
    p.add_argument("--refresh", action="store_true")


def _ingest(args: argparse.Namespace) -> None:
    """Map a provider feed onto the event ledger — validates the seam."""
    result = _resolve_ingest(args)
    if result is None:
        print(
            "no data — statsbomb needs --match-id (+--competition-id/--season-id) "
            "or --file; sportmonks needs SPORTMONKS_API_TOKEN or --file"
        )
        return
    print(json.dumps(result.provenance, indent=2))
    for e in result.events[:10]:
        print(f"  {e.minute:3d}' {e.type.value:12s} {e.team.value:4s} {e.player}")


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
    runp = sub.add_parser("run")
    runp.add_argument("--real", action="store_true", help="ingest a real feed instead of synthetic")
    _add_ingest_args(runp)
    rt = sub.add_parser("redteam")
    rt.add_argument("--seed", type=int, default=137)
    comp = sub.add_parser("compliance")
    comp.add_argument("--seed", type=int, default=137)
    comp.add_argument("--match-id", default="match_art50")
    comp.add_argument(
        "--real", action="store_true", help="run against an ingested real feed instead of synthetic"
    )
    sub.add_parser("evaluate")
    ing = sub.add_parser("ingest")
    _add_ingest_args(ing)
    # comp's own --match-id doubles as the provider match id under --real
    _add_ingest_args(comp, include_match_id=False)
    args = p.parse_args()

    {
        "redteam": _redteam,
        "compliance": _compliance,
        "evaluate": _evaluate,
        "ingest": _ingest,
    }.get(args.cmd, _run)(args)


if __name__ == "__main__":
    main()
