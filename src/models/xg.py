"""Expected goals (xG) model."""

from __future__ import annotations

import math

from src.events.schema import Event, Position


def shot_xg(position: Position, body_part: str = "right_foot", on_target: bool = True) -> float:
    """Compute xG from shot position. Distance/angle based heuristic."""
    dx = 120 - position.x
    dy = position.y - 40
    dist = max(1.0, math.hypot(dx, dy))
    angle = math.atan2(abs(dy) + 1, dx)
    base = (1.0 / (1.0 + (dist / 9.0))) * (angle / 1.4)
    if body_part == "head":
        base *= 0.85
    if not on_target:
        base *= 0.6
    return round(min(0.99, max(0.01, base)), 3)


def event_xg(event: Event) -> float | None:
    if event.type.value not in ("shot", "goal"):
        return None
    bp = event.metadata.get("body_part", "right_foot")
    on_target = event.outcome in ("on_target", "goal")
    return shot_xg(event.position, bp, on_target)
