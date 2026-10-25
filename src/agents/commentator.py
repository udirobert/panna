"""Commentator agent: timed broadcast natural-language commentary."""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.events.schema import CommentaryEntry, Insight, KeyMoment


class CommentatorAgent(BaseAgent):
    name = "commentator"

    def run(self, context: dict) -> list[CommentaryEntry]:
        key_moments: list[KeyMoment] = context.get("key_moments", [])
        insights: list[Insight] = context.get("insights", [])
        out: list[CommentaryEntry] = []

        # Sort key moments by minute
        for km in sorted(key_moments, key=lambda k: k.minute)[:25]:
            text = self._comment(km, insights)
            sec = 0
            out.append(
                CommentaryEntry(
                    minute=km.minute,
                    second=sec,
                    text=text,
                    tone="broadcast",
                    insight_ids=[i.id for i in insights if km.event_id in i.evidence][:2],
                )
            )

        # Add a couple of insight-driven commentary lines
        for ins in insights[:5]:
            out.append(
                CommentaryEntry(
                    minute=min(
                        90, max(1, int(ins.timestamp.split(":")[0]) if ":" in ins.timestamp else 45)
                    ),
                    second=0,
                    text=f"Analyst note: {ins.claim}",
                    tone="analysis",
                    insight_ids=[ins.id],
                )
            )
        return out

    @staticmethod
    def _comment(km: KeyMoment, insights: list[Insight]) -> str:
        templates = {
            "goal": "GOAL! {desc}",
            "shot": "Chance! {desc}",
            "tackle": "Crunching tackle — {desc}",
            "formation_change": "Tactical shift — {desc}",
            "set_piece": "Set piece opportunity — {desc}",
            "foul": "Foul given — {desc}",
        }
        prefix = templates.get(km.type, "")
        return prefix.format(desc=km.description) if prefix else km.description
