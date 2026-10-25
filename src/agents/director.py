"""Director agent: orchestration, prioritization, failure recovery."""

from __future__ import annotations

import time

from src.agents.analyst import AnalystAgent
from src.agents.base import BaseAgent
from src.agents.commentator import CommentatorAgent
from src.agents.recap import RecapAgent
from src.agents.scout import ScoutAgent
from src.events.schema import AgentHealth


class DirectorAgent(BaseAgent):
    name = "director"

    def __init__(self) -> None:
        self.scout = ScoutAgent()
        self.analyst = AnalystAgent()
        self.commentator = CommentatorAgent()
        self.recap = RecapAgent()
        self.health: dict[str, AgentHealth] = {}

    def run(self, context: dict) -> dict:
        events = context["events"]
        shared: dict = {"events": events}
        errors: dict[str, str] = {}

        # 1. Scout
        km, err = self.scout.safe_run({"events": events})
        if err:
            errors["scout"] = err
            km = []
            self.health["scout"] = AgentHealth(agent="scout", status="down", error=err)
        else:
            self.health["scout"] = AgentHealth(agent="scout", status="healthy")
        shared["key_moments"] = km or []

        # 2. Analyst (retry once)
        insights, err = self.analyst.safe_run({"events": events})
        if err:
            time.sleep(0.1)
            insights, err = self.analyst.safe_run({"events": events})
        if err:
            errors["analyst"] = err
            insights = []
            self.health["analyst"] = AgentHealth(agent="analyst", status="down", error=err)
        else:
            self.health["analyst"] = AgentHealth(agent="analyst", status="healthy")
        shared["insights"] = insights or []

        # 3. Degraded fallback: if analyst down, derive minimal insights from scout
        if not shared["insights"] and shared["key_moments"]:
            from src.events.schema import Insight

            shared["insights"] = [
                Insight(
                    id=f"ins_fallback_{km.id}",
                    type="key_moment",
                    claim=km.description,
                    value=km.importance,
                    confidence=0.5,
                    evidence=[km.event_id],
                    agent="director-fallback",
                    timestamp="0:00",
                )
                for km in shared["key_moments"][:5]
            ]
            if "analyst" in errors:
                self.health["analyst"] = AgentHealth(
                    agent="analyst", status="degraded", error=errors["analyst"]
                )

        # 4. Commentator (fallback to template if fails)
        commentary, err = self.commentator.safe_run(shared)
        if err:
            errors["commentator"] = err
            commentary = []
            self.health["commentator"] = AgentHealth(agent="commentator", status="down", error=err)
        else:
            self.health["commentator"] = AgentHealth(agent="commentator", status="healthy")
        shared["commentary"] = commentary or []

        # 5. Prioritize broadcast feed: goals + high-importance moments first
        feed = self._prioritize(shared)

        return {
            "key_moments": shared["key_moments"],
            "insights": shared["insights"],
            "commentary": shared["commentary"],
            "feed": feed,
            "health": {k: v.model_dump() for k, v in self.health.items()},
            "errors": errors,
        }

    @staticmethod
    def _prioritize(shared: dict) -> list[dict]:
        items = []
        for km in shared.get("key_moments", []):
            items.append(
                {
                    "kind": "moment",
                    "minute": km.minute,
                    "importance": km.importance,
                    "text": km.description,
                }
            )
        for c in shared.get("commentary", []):
            items.append(
                {"kind": "commentary", "minute": c.minute, "importance": 0.5, "text": c.text}
            )
        items.sort(key=lambda x: (x["minute"], -x["importance"]))
        return items
