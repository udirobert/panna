"""Red-team harness: plant known-false lines and measure the Verifier's catch
rate — the "prove it catches a wrong number" demo every winner shipped.

Planted attack classes (each maps to a real failure mode a hallucinating model
produces):

- ``inflate_xg``      — an xG total multiplied up (the classic invented stat)
- ``wrong_player``    — right stat, wrong attribution
- ``invented_stat``   — a plausible-looking number nothing produced
- ``wrong_minute``    — a goal claimed at a minute no goal happened
- ``fabricated_score``— a scoreline the running ledger contradicts
- ``ghost_event``     — evidence ids pointing at events that don't exist

Each planted line goes through the real ``VerifierAgent`` — the same gate the
broadcast uses. The report counts caught/missed per class plus the honest-line
rejection rate (the false-positive tax the winners reported too).

Run:  ``panna-run redteam --seed 137``  or ``python -m src.cli redteam``
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.agents.director import DirectorAgent
from src.agents.verifier import VerifierAgent, _Facts  # noqa: SLF001
from src.events.generator import MatchConfig, SyntheticMatchGenerator
from src.events.schema import CommentaryEntry, Insight, Team

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


def _planted_lines(events: list, facts: _Facts) -> list[tuple[str, Insight | CommentaryEntry]]:
    """One fabricated line per attack class."""
    goal = next(e for e in events if e.type.value == "goal")
    wrong_team = Team.AWAY if goal.team == Team.HOME else Team.HOME
    # a real player who is definitively NOT the top influence for that team
    ranked = facts.influence[wrong_team]
    top = ranked[0]["player"] if ranked else "P99"
    non_top = next((r["player"] for r in ranked if r["player"] != top), "P10")
    # a minute at least 2 away from every real goal (the check allows ±1)
    no_goal_minute = next(
        m for m in range(1, 89) if all(abs(m - g) > 1 for g in facts.goal_minutes)
    )
    h, a = facts.score_at(90)

    return [
        (
            "inflate_xg",
            Insight(
                id="rt_inflate",
                type="narrative",
                claim=f"Home dominated with {facts.home_xg * 1.5:.2f} xG",
                value=facts.home_xg * 1.5,
                confidence=0.9,
                evidence=[goal.id],
            ),
        ),
        (
            "wrong_player",
            Insight(
                id="rt_player",
                type="player_influence",
                claim=f"{wrong_team.value.title()} {non_top} the most influential",
                value=0.9,
                confidence=0.9,
                evidence=[goal.id],
            ),
        ),
        (
            "invented_stat",
            CommentaryEntry(
                id="rt_invented",
                minute=goal.minute,
                second=30,
                text="A sprint of 37.84 km/h sealed the breakaway!",
            ),
        ),
        (
            "wrong_minute",
            CommentaryEntry(
                id="rt_minute",
                minute=no_goal_minute,
                second=10,
                text=f"GOAL at {no_goal_minute}'! The net ripples again!",
            ),
        ),
        (
            "fabricated_score",
            CommentaryEntry(
                id="rt_score",
                minute=80,
                second=0,
                text=f"And that makes it {h + 2}-{a} — a rout now!",
            ),
        ),
        (
            "ghost_event",
            Insight(
                id="rt_ghost",
                type="key_moment",
                claim="The disallowed strike changed everything",
                value=0.8,
                confidence=0.8,
                evidence=["evt_9999", "evt_0000"],
            ),
        ),
    ]


def run_redteam(seed: int = 137, match_id: str = "match_rt") -> dict[str, Any]:
    """Full pass: honest broadcast + planted attacks through the same gate."""
    events = SyntheticMatchGenerator(MatchConfig(match_id=match_id, seed=seed)).generate()
    result = DirectorAgent().run({"events": events})
    verifier = VerifierAgent()
    facts = _Facts(events)

    # honest-line rejection rate (false-positive tax)
    honest = result.get("insights", []) + result.get("commentary", [])
    honest_verdicts = [v for v in result.get("verdicts", {}).values()]
    honest_rejected = sum(1 for v in honest_verdicts if v.status == "rejected")

    # planted attacks
    attacks: list[dict] = []
    for name, item in _planted_lines(events, facts):
        if isinstance(item, Insight):
            v = verifier.verify_insight(item, events, facts)
        else:
            v = verifier.verify_commentary(item, events, {}, facts)
        caught = v.status in ("rejected", "repaired")
        attacks.append(
            {
                "attack": name,
                "line": getattr(item, "claim", None) or item.text,
                "verdict": v.status,
                "reason": v.reason,
                "caught": caught,
            }
        )

    caught_n = sum(1 for a in attacks if a["caught"])
    return {
        "match_id": match_id,
        "seed": seed,
        "events": len(events),
        "honest_items": len(honest),
        "honest_rejected": honest_rejected,
        "honest_rejection_rate": round(honest_rejected / max(len(honest), 1), 3),
        "attacks": attacks,
        "planted": len(attacks),
        "caught": caught_n,
        "catch_rate": round(caught_n / len(attacks), 3),
        "verification_summary": result.get("verification", {}),
        "health": result.get("health", {}),
    }


def write_report(report: dict, path: Path | None = None) -> Path:
    """Render the judge-facing markdown report (the winners' reports/ pattern)."""
    path = path or REPORTS_DIR / "verifier-redteam.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Verifier red-team report",
        "",
        f"Match `{report['match_id']}` (seed {report['seed']}) — "
        f"{report['events']} synthetic events.",
        "",
        "## Result",
        "",
        f"- **{report['caught']}/{report['planted']} planted false lines caught** "
        f"(catch rate {report['catch_rate']:.0%})",
        f"- Honest-line rejection rate: **{report['honest_rejection_rate']:.1%}** "
        f"({report['honest_rejected']} of {report['honest_items']} legitimate lines held)",
        f"- Gate summary: `{json.dumps(report['verification_summary'])}`",
        "",
        "## Planted attacks",
        "",
        "| attack | line | verdict | caught |",
        "|---|---|---|---|",
    ]
    for a in report["attacks"]:
        lines.append(
            f"| `{a['attack']}` | {a['line'][:60]} | {a['verdict']} "
            f"| {'yes' if a['caught'] else '**MISSED**'} |"
        )
    lines += [
        "",
        "Method: each fabricated line ran through the production VerifierAgent — "
        "the same deterministic recount gate that sits between drafted lines and "
        "the broadcast feed. Nothing was verified by hand.",
        "",
    ]
    path.write_text("\n".join(lines))
    return path
