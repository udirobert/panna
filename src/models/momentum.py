"""Momentum: rolling xG window per team."""

from __future__ import annotations

from src.events.schema import Event, Team


def momentum(events: list[Event], window_minutes: int = 10) -> list[dict]:
    """Rolling xG difference (home - away) per window_minutes block."""
    out = []
    max_min = max((e.minute for e in events), default=0)
    for start in range(0, max_min, window_minutes):
        end = start + window_minutes
        home_xg = 0.0
        away_xg = 0.0
        for e in events:
            if not (start <= e.minute < end):
                continue
            if e.type.value in ("shot", "goal"):
                xg = float(e.metadata.get("xg", 0.0))
                if e.team == Team.HOME:
                    home_xg += xg
                else:
                    away_xg += xg
        out.append(
            {
                "window": f"{start}'-{end}'",
                "home_xg": round(home_xg, 3),
                "away_xg": round(away_xg, 3),
                "momentum": round(home_xg - away_xg, 3),
            }
        )
    return out
