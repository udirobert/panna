"""Pressing intensity (PPDA) model."""

from __future__ import annotations

from src.events.schema import Event, Team


def ppda(events: list[Event], team: Team, window_minutes: int = 15) -> float:
    """Passes allowed per defensive action (lower = more pressing)."""
    opp = Team.AWAY if team == Team.HOME else Team.HOME
    passes = 0
    da = 0
    for e in events:
        if e.team == opp and e.type.value == "pass":
            passes += 1
        if e.team == team and e.type.value in ("tackle", "interception", "pressure"):
            da += 1
    if da == 0:
        return float("inf")
    return round(passes / da, 2)
