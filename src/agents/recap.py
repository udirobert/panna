"""Recap agent: post-match summary."""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.events.schema import Insight, KeyMoment


class RecapAgent(BaseAgent):
    name = "recap"

    def run(self, context: dict) -> str:
        insights: list[Insight] = context.get("insights", [])
        key_moments: list[KeyMoment] = context.get("key_moments", [])
        goals = [km for km in key_moments if km.type == "goal"]
        top = sorted(insights, key=lambda i: i.confidence, reverse=True)[:4]

        lines = []
        lines.append("FULL-TIME RECAP")
        lines.append(f"Goals: {len(goals)}")
        for g in goals:
            lines.append(f"  - {g.description}")
        lines.append("")
        lines.append("Key insights:")
        for i in top:
            lines.append(f"  - {i.claim}")
        lines.append("")
        lines.append(f"Total key moments flagged: {len(key_moments)}")
        return "\n".join(lines)
