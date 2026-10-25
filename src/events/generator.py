"""Synthetic football match event generator (seeded, deterministic)."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .schema import Event, EventType, Position, Team


@dataclass
class MatchConfig:
    match_id: str = "match_001"
    seed: int = 42
    home_team: str = "Home FC"
    away_team: str = "Away United"
    duration_minutes: int = 90
    home_formation: str = "4-3-3"
    away_formation: str = "4-4-2"


@dataclass
class SyntheticMatchGenerator:
    config: MatchConfig = field(default_factory=MatchConfig)
    rng: random.Random = field(init=False)

    def __post_init__(self) -> None:
        self.rng = random.Random(self.config.seed)  # noqa: S311

    def generate(self) -> list[Event]:
        events: list[Event] = []
        counter = [0]

        def new_id() -> str:
            counter[0] += 1
            return f"evt_{counter[0]:04d}"

        # Formation change at kickoff
        events.append(
            Event(
                id=new_id(),
                match_id=self.config.match_id,
                minute=0,
                second=0,
                type=EventType.FORMATION_CHANGE,
                player="Coach",
                team=Team.HOME,
                position=Position(x=60, y=40),
                metadata={"formation": self.config.home_formation, "side": "home"},
            )
        )

        # Generate ~1500 events across 90 minutes
        minute = 0
        second = 0
        possession = Team.HOME
        seq = 0
        while minute < self.config.duration_minutes:
            seq += 1
            team = possession
            # ~17 events per minute
            if self.rng.random() < 0.05:
                # shot
                x = self.rng.uniform(95, 118)
                y = self.rng.uniform(20, 60)
                on_target = self.rng.random() < 0.35
                is_goal = on_target and self.rng.random() < 0.12
                etype = EventType.GOAL if is_goal else EventType.SHOT
                outcome = "goal" if is_goal else ("on_target" if on_target else "off_target")
                ev = Event(
                    id=new_id(),
                    match_id=self.config.match_id,
                    minute=minute,
                    second=second,
                    type=etype,
                    player=f"P{self.rng.randint(1, 11)}",
                    team=team,
                    position=Position(x=x, y=y),
                    outcome=outcome,
                    metadata={
                        "body_part": self.rng.choice(["right_foot", "left_foot", "head"]),
                        "xg": round(self._xg(x, y), 3),
                    },
                )
                events.append(ev)
                if is_goal:
                    possession = Team.AWAY if team == Team.HOME else Team.HOME
            elif self.rng.random() < 0.08:
                # tackle
                x = self.rng.uniform(30, 90)
                y = self.rng.uniform(10, 70)
                success = self.rng.random() < 0.6
                events.append(
                    Event(
                        id=new_id(),
                        match_id=self.config.match_id,
                        minute=minute,
                        second=second,
                        type=EventType.TACKLE,
                        player=f"P{self.rng.randint(1, 11)}",
                        team=team,
                        position=Position(x=x, y=y),
                        outcome="success" if success else "unsuccessful",
                    )
                )
                if success:
                    possession = Team.AWAY if team == Team.HOME else Team.HOME
            elif self.rng.random() < 0.04:
                # foul
                x = self.rng.uniform(20, 100)
                y = self.rng.uniform(10, 70)
                card = (
                    self.rng.choice(["none", "none", "none", "yellow", "red"])
                    if self.rng.random() < 0.3
                    else "none"
                )
                events.append(
                    Event(
                        id=new_id(),
                        match_id=self.config.match_id,
                        minute=minute,
                        second=second,
                        type=EventType.FOUL,
                        player=f"P{self.rng.randint(1, 11)}",
                        team=team,
                        position=Position(x=x, y=y),
                        outcome=card,
                        metadata={"card": card},
                    )
                )
            elif self.rng.random() < 0.06:
                # set piece
                sp = self.rng.choice(["corner", "free_kick", "throw_in"])
                events.append(
                    Event(
                        id=new_id(),
                        match_id=self.config.match_id,
                        minute=minute,
                        second=second,
                        type=EventType.SET_PIECE,
                        player=f"P{self.rng.randint(1, 11)}",
                        team=team,
                        position=Position(x=self.rng.uniform(0, 120), y=self.rng.uniform(0, 80)),
                        metadata={"set_piece_type": sp},
                    )
                )
            elif self.rng.random() < 0.03:
                # substitution
                events.append(
                    Event(
                        id=new_id(),
                        match_id=self.config.match_id,
                        minute=minute,
                        second=second,
                        type=EventType.SUBSTITUTION,
                        player=f"P{self.rng.randint(1, 11)}",
                        team=team,
                        position=Position(x=60, y=40),
                        metadata={
                            "player_in": f"P{self.rng.randint(1, 11)}",
                            "player_out": f"P{self.rng.randint(1, 11)}",
                        },
                    )
                )
            elif self.rng.random() < 0.02:
                # formation change
                new_form = self.rng.choice(["4-3-3", "4-4-2", "3-5-2", "4-2-3-1"])
                events.append(
                    Event(
                        id=new_id(),
                        match_id=self.config.match_id,
                        minute=minute,
                        second=second,
                        type=EventType.FORMATION_CHANGE,
                        player="Coach",
                        team=team,
                        position=Position(x=60, y=40),
                        metadata={"formation": new_form},
                    )
                )
            else:
                # pass
                x = self.rng.uniform(10, 110)
                y = self.rng.uniform(5, 75)
                ex = x + self.rng.uniform(-25, 25)
                ey = y + self.rng.uniform(-20, 20)
                ex = max(0, min(120, ex))
                ey = max(0, min(80, ey))
                success = self.rng.random() < 0.82
                pass_type = self.rng.choice(
                    ["short", "short", "short", "long", "through", "cross", "back"]
                )
                events.append(
                    Event(
                        id=new_id(),
                        match_id=self.config.match_id,
                        minute=minute,
                        second=second,
                        type=EventType.PASS,
                        player=f"P{self.rng.randint(1, 11)}",
                        team=team,
                        position=Position(x=x, y=y),
                        end_location=Position(x=ex, y=ey),
                        outcome="success" if success else "unsuccessful",
                        metadata={
                            "pass_type": pass_type,
                            "distance": round(((ex - x) ** 2 + (ey - y) ** 2) ** 0.5, 1),
                        },
                    )
                )
                if not success:
                    possession = Team.AWAY if team == Team.HOME else Team.HOME

            # advance time ~3.5s per event
            second += 4
            if second >= 60:
                minute += second // 60
                second = second % 60

        # final whistle marker
        events.append(
            Event(
                id=new_id(),
                match_id=self.config.match_id,
                minute=self.config.duration_minutes,
                second=0,
                type=EventType.POSSESSION_CHANGE,
                player="Referee",
                team=Team.HOME,
                position=Position(x=60, y=40),
                metadata={"event": "full_time"},
            )
        )
        return events

    @staticmethod
    def _xg(x: float, y: float) -> float:
        # Simple xG: distance to goal center (120,40), angle
        import math

        dx = 120 - x
        dy = y - 40
        dist = max(1.0, (dx * dx + dy * dy) ** 0.5)
        angle = math.atan2(abs(dy) + 1, dx)
        base = 0.95 * (1.0 / (1.0 + (dist / 8.0))) * (angle / 1.5)
        return min(0.99, max(0.01, base))
