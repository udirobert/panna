"""Formation effectiveness: shots/xG generated while in a formation."""

from __future__ import annotations

from collections import defaultdict

from src.events.schema import Event, Team


def formation_effectiveness(events: list[Event], team: Team) -> dict[str, dict]:
    """For each formation a team played in, aggregate shots and xG."""
    # Track current formation
    current = "4-3-3"
    stats: dict[str, dict] = defaultdict(lambda: {"shots": 0, "xg": 0.0, "minutes": 0})
    last_minute = 0
    for e in events:
        if e.type.value == "formation_change" and e.team == team:
            dur = e.minute - last_minute
            stats[current]["minutes"] += max(0, dur)
            current = e.metadata.get("formation", current)
            last_minute = e.minute
        if e.team == team and e.type.value in ("shot", "goal"):
            xg = e.metadata.get("xg", 0.0)
            stats[current]["shots"] += 1
            stats[current]["xg"] += float(xg)
    # tail
    if events:
        stats[current]["minutes"] += max(0, (events[-1].minute - last_minute))
    return {
        k: {"shots": v["shots"], "xg": round(v["xg"], 3), "minutes": v["minutes"]}
        for k, v in stats.items()
    }
