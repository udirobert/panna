"""Analyst agent: tactical insights with evidence citations."""

from __future__ import annotations

import uuid

from src.agents.base import BaseAgent
from src.events.schema import Event, Insight, Team
from src.models.formation import formation_effectiveness
from src.models.influence import player_influence
from src.models.momentum import momentum
from src.models.pressing import ppda
from src.models.xg import event_xg


class AnalystAgent(BaseAgent):
    name = "analyst"

    def run(self, context: dict) -> list[Insight]:
        events: list[Event] = context["events"]
        insights: list[Insight] = []

        # 1. Total xG per team
        home_xg = 0.0
        away_xg = 0.0
        shot_events: list[Event] = []
        for e in events:
            if e.type.value in ("shot", "goal"):
                xg = event_xg(e)
                if xg is None:
                    xg = float(e.metadata.get("xg", 0.0))
                shot_events.append(e)
                if e.team == Team.HOME:
                    home_xg += xg
                else:
                    away_xg += xg
        insights.append(
            Insight(
                id=f"ins_{uuid.uuid4().hex[:8]}",
                type="xg_total",
                claim=f"Home xG {home_xg:.2f} vs Away xG {away_xg:.2f}",
                value=round(home_xg - away_xg, 3),
                confidence=0.9,
                evidence=[e.id for e in shot_events[:8]],
            )
        )

        # 2. Pressing intensity (PPDA)
        for team in (Team.HOME, Team.AWAY):
            p = ppda(events, team)
            insights.append(
                Insight(
                    id=f"ins_{uuid.uuid4().hex[:8]}",
                    type="pressing_intensity",
                    claim=f"{team.value} PPDA = {p} (lower = more pressing)",
                    value=p if p != float("inf") else 999.0,
                    confidence=0.8,
                    evidence=[
                        e.id
                        for e in events
                        if e.team == team and e.type.value in ("tackle", "interception", "pressure")
                    ][:6],
                )
            )

        # 3. Formation effectiveness
        for team in (Team.HOME, Team.AWAY):
            fe = formation_effectiveness(events, team)
            for form, stats in fe.items():
                if stats["minutes"] < 5:
                    continue
                insights.append(
                    Insight(
                        id=f"ins_{uuid.uuid4().hex[:8]}",
                        type="formation_effectiveness",
                        claim=(
                            f"{team.value} in {form}: {stats['shots']} shots, "
                            f"xG {stats['xg']} over {stats['minutes']} min"
                        ),
                        value=stats["xg"],
                        confidence=0.75,
                        evidence=[
                            e.id
                            for e in events
                            if e.team == team and e.type.value in ("shot", "goal")
                        ][:4],
                    )
                )

        # 4. Player influence
        for team in (Team.HOME, Team.AWAY):
            ranked = player_influence(events, team)
            if ranked:
                top = ranked[0]
                insights.append(
                    Insight(
                        id=f"ins_{uuid.uuid4().hex[:8]}",
                        type="player_influence",
                        claim=(
                            f"Most influential {team.value} player: "
                            f"{top['player']} ({top['influence']})"
                        ),
                        value=top["influence"],
                        confidence=0.7,
                        evidence=[e.id for e in events if e.player == top["player"]][:5],
                    )
                )

        # 5. Momentum shifts
        mom = momentum(events)
        # find biggest swing
        if mom:
            biggest = max(mom, key=lambda m: abs(m["momentum"]))
            insights.append(
                Insight(
                    id=f"ins_{uuid.uuid4().hex[:8]}",
                    type="momentum_shift",
                    claim=(
                        f"Biggest momentum swing: {biggest['window']} "
                        f"({biggest['momentum']:+.2f} xG)"
                    ),
                    value=biggest["momentum"],
                    confidence=0.7,
                    evidence=_window_evidence(events, biggest["window"]),
                )
            )

        return insights


def _window_evidence(events: list[Event], window: str) -> list[str]:
    """Shot/goal event ids inside a momentum window like "70'-80'".

    (The old parser split on the apostrophe and produced int("-80").)
    """
    try:
        start = int(window.split("-")[0].strip().rstrip("'"))
        end = int(window.split("-")[1].strip().rstrip("'"))
    except (ValueError, IndexError):
        return []
    return [e.id for e in events if start <= e.minute < end and e.type.value in ("shot", "goal")][
        :6
    ]
