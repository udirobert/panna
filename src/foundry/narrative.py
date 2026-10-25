"""Concrete Foundry-backed narrative agents.

Two agentic passes sit on top of the deterministic engines:

- :class:`NarratorAgent` — the *Booth*. One structured Foundry call turns a
  match's key moments + insights into timed broadcast commentary lines. Falls
  back to the deterministic template commentator when Foundry is unavailable
  or the reply can't be parsed.
- :class:`VerdictAgent` — the full-time *case*. One Foundry call turns the
  recap facts into an editorial verdict. Falls back to the deterministic
  template recap.

Both are traced; both degrade to identical local output offline, so the
pipeline and demo never depend on the network.
"""

from __future__ import annotations

import json
from typing import Any

from src.agents.commentator import CommentatorAgent
from src.agents.recap import RecapAgent
from src.events.schema import CommentaryEntry
from src.foundry.agents import FoundryAgent


class NarratorAgent(FoundryAgent):
    name = "booth"

    def __init__(self, match_id: str = "match_001") -> None:
        self.match_id = match_id
        self._fallback_engine = CommentatorAgent()

    def _system_prompt(self) -> str:
        return (
            "You are 'The Booth', a broadcast football commentator. Write "
            "punchy, timed, professional play-by-play lines. Each line carries "
            "a match minute. Cite the tactical insight that justifies it when "
            "one applies. Vary tone between 'broadcast' and 'analysis'. "
            "Respond ONLY with a JSON array of objects with keys: "
            "minute (int), second (int, 0-59), text (str), "
            "tone ('broadcast'|'analysis'), insight_ids (array of str, may be empty)."
        )

    def _user_payload(self, context: dict) -> str:
        moments = context.get("key_moments", [])
        insights = context.get("insights", [])
        return json.dumps(
            {
                "key_moments": [
                    {
                        "minute": m.minute,
                        "type": m.type,
                        "text": m.description,
                        "importance": m.importance,
                        "insight_ids": getattr(m, "insight_ids", []) or [],
                    }
                    for m in moments[:25]
                ],
                "insights": [
                    {"id": i.id, "type": i.type, "claim": i.claim, "confidence": i.confidence}
                    for i in insights[:10]
                ],
            },
            default=str,
        )

    def _fallback(self, context: dict) -> Any:
        return self._fallback_engine.run(context)

    def _fallback_safe(self, context: dict) -> Any:
        return []

    def _parse(self, raw: str, context: dict) -> Any:
        data = json.loads(raw)
        if not isinstance(data, list):
            return None
        out: list[CommentaryEntry] = []
        for row in data:
            if not isinstance(row, dict) or "text" not in row:
                continue
            try:
                out.append(
                    CommentaryEntry(
                        minute=int(row.get("minute", 0)),
                        second=max(0, min(59, int(row.get("second", 0)))),
                        text=str(row["text"]),
                        tone=str(row.get("tone", "broadcast")),
                        insight_ids=[str(x) for x in (row.get("insight_ids") or [])][:2],
                    )
                )
            except (TypeError, ValueError):
                continue
        return out or None


class VerdictAgent(FoundryAgent):
    name = "chalk-verdict"

    def __init__(self, match_id: str = "match_001") -> None:
        self.match_id = match_id
        self._fallback_engine = RecapAgent()

    def _system_prompt(self) -> str:
        return (
            "You are a football editor writing the full-time case file in the "
            "style of an illustrated match report: a crisp headline verdict, "
            "a three-to-five line narrative, and the decisive moments. Plain, "
            "confident, no jargon. Respond with plain text only."
        )

    def _user_payload(self, context: dict) -> str:
        insights = context.get("insights", [])
        moments = context.get("key_moments", [])
        return json.dumps(
            {
                "insights": [
                    {
                        "type": i.type,
                        "claim": i.claim,
                        "confidence": i.confidence,
                    }
                    for i in insights[:6]
                ],
                "key_moments": [
                    {
                        "minute": m.minute,
                        "type": m.type,
                        "text": m.description,
                        "importance": m.importance,
                    }
                    for m in moments[:15]
                ],
            },
            default=str,
        )

    def _fallback(self, context: dict) -> Any:
        return self._fallback_engine.run(context)

    def _parse(self, raw: str, context: dict) -> Any:
        return raw


def booth_commentary(match_id: str, context: dict) -> dict[str, Any]:
    """Booth pass: Foundry commentary lines with deterministic fallback."""
    return NarratorAgent(match_id=match_id).generate(context, "booth.narrate")


def verdict_recap(match_id: str, insights, key_moments) -> dict[str, Any]:
    """Full-time case: Foundry verdict with deterministic fallback."""
    return VerdictAgent(match_id=match_id).generate(
        {"insights": insights, "key_moments": key_moments}, "chalk.verdict"
    )
