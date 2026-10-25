"""Scout agent: event detection + key moment flagging."""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.events.schema import Event, KeyMoment


class ScoutAgent(BaseAgent):
    name = "scout"

    IMPORTANT_TYPES = {"shot", "goal", "tackle", "formation_change", "set_piece", "foul"}

    def run(self, context: dict) -> list[KeyMoment]:
        events: list[Event] = context["events"]
        out: list[KeyMoment] = []
        for e in events:
            if e.type.value not in self.IMPORTANT_TYPES:
                continue
            importance = self._importance(e)
            if importance < 0.3:
                continue
            out.append(
                KeyMoment(
                    id=f"km_{e.id}",
                    event_id=e.id,
                    minute=e.minute,
                    type=e.type.value,
                    importance=round(importance, 2),
                    description=self._describe(e),
                    evidence=[e.id],
                )
            )
        # sort by importance desc, cap
        out.sort(key=lambda k: k.importance, reverse=True)
        return out[:40]

    @staticmethod
    def _importance(e: Event) -> float:
        if e.type.value == "goal":
            return 1.0
        if e.type.value == "shot":
            xg = float(e.metadata.get("xg", 0.1))
            return min(1.0, 0.4 + xg)
        if e.type.value == "formation_change":
            return 0.7
        if e.type.value == "set_piece":
            return 0.5
        if e.type.value == "foul" and e.metadata.get("card") in ("yellow", "red"):
            return 0.6
        if e.type.value == "tackle":
            return 0.4 if e.outcome == "success" else 0.25
        return 0.3

    @staticmethod
    def _describe(e: Event) -> str:
        if e.type.value == "goal":
            return f"GOAL! {e.player} ({e.team.value}) at {e.minute}'"
        if e.type.value == "shot":
            return f"Shot by {e.player} ({e.team.value}) at {e.minute}' — xG {e.metadata.get('xg')}"
        if e.type.value == "formation_change":
            return f"{e.team.value} switches to {e.metadata.get('formation')} at {e.minute}'"
        if e.type.value == "set_piece":
            return f"{e.metadata.get('set_piece_type')} for {e.team.value} at {e.minute}'"
        if e.type.value == "foul":
            return f"Foul by {e.player} ({e.team.value}) at {e.minute}' ({e.metadata.get('card')})"
        if e.type.value == "tackle":
            outcome = "won" if e.outcome == "success" else "lost"
            return f"Tackle {outcome} by {e.player} ({e.team.value}) at {e.minute}'"
        return f"{e.type.value} by {e.player} at {e.minute}'"
