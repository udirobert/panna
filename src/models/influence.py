"""Player influence: simple xT/possession contribution ranking."""

from __future__ import annotations

from collections import defaultdict

from src.events.schema import Event, Team


def player_influence(events: list[Event], team: Team) -> list[dict]:
    """Rank players by combined pass success + shots + tackles."""
    scores: dict[str, float] = defaultdict(float)
    for e in events:
        if e.team != team:
            continue
        if e.type.value == "pass" and e.outcome == "success":
            scores[e.player] += 0.3 + (e.metadata.get("distance", 0) / 100.0)
        elif e.type.value in ("shot", "goal"):
            scores[e.player] += 1.0 + float(e.metadata.get("xg", 0.0))
        elif e.type.value == "tackle" and e.outcome == "success":
            scores[e.player] += 0.6
        elif e.type.value == "interception":
            scores[e.player] += 0.5
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [{"player": p, "influence": round(s, 3)} for p, s in ranked[:11]]
