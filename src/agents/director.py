"""Director agent: orchestration, prioritization, failure recovery."""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.commentator import CommentatorAgent
from src.agents.recap import RecapAgent
from src.agents.scout import ScoutAgent
from src.events.schema import AgentHealth


class DirectorAgent(BaseAgent):
    name = "director"

    def __init__(self) -> None:
        self.scout = ScoutAgent()
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

        # 2. Analyst (Chalk): reasoning on the Microsoft Agent Framework when
        #    Foundry is configured — a tool-calling loop over the match; the
        #    deterministic analyst otherwise. Never throws (it falls back).
        from src.foundry import maf as _maf

        chalk = _maf.chalk_insights(events, self._match_id(shared))
        insights = chalk["insights"]
        shared["insights"] = insights or []
        shared["reasoning_source"] = chalk["source"]
        shared["reasoning_model"] = chalk["model"]
        shared["reasoning_tool_calls"] = chalk["tool_calls"]
        if chalk["error"]:
            errors["analyst"] = chalk["error"]
            self.health["analyst"] = AgentHealth(
                agent="analyst", status="degraded", error=chalk["error"]
            )
        else:
            self.health["analyst"] = AgentHealth(
                agent="analyst",
                status="healthy",
                last_ok=chalk["model"] if chalk["source"] == "foundry" else None,
            )

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

        # 4. Commentator (Booth): Foundry LLM narrative when available,
        #    deterministic template otherwise — always traced.
        from src.foundry import narrative as _narrative

        booth = None
        try:
            booth = _narrative.booth_commentary(self._match_id(shared), shared)
        except Exception as exc:  # noqa: BLE001
            errors["commentator"] = f"booth: {exc}"
        if booth is not None and booth.get("result"):
            shared["commentary"] = booth["result"]
            shared["commentary_source"] = booth["source"]
            self.health["commentator"] = AgentHealth(
                agent="commentator",
                status="healthy",
                last_ok=booth.get("model"),
                error=None if booth["status"] == "ok" else f"fallback ({booth['status']})",
            )
        else:
            commentary, err = self.commentator.safe_run(shared)
            if err:
                errors["commentator"] = errors.get("commentator", err)
                shared["commentary"] = []
                self.health["commentator"] = AgentHealth(
                    agent="commentator", status="down", error=err
                )
            else:
                shared["commentary"] = commentary or []
                self.health["commentator"] = AgentHealth(agent="commentator", status="healthy")
            shared["commentary_source"] = "template"

        # 5. Prioritize broadcast feed: goals + high-importance moments first
        feed = self._prioritize(shared)

        return {
            "key_moments": shared["key_moments"],
            "insights": shared["insights"],
            "commentary": shared["commentary"],
            "commentary_source": shared.get("commentary_source", "template"),
            "reasoning_source": shared.get("reasoning_source", "template"),
            "reasoning_model": shared.get("reasoning_model"),
            "reasoning_tool_calls": shared.get("reasoning_tool_calls", 0),
            "feed": feed,
            "health": {k: v.model_dump() for k, v in self.health.items()},
            "errors": errors,
        }

    @staticmethod
    def _match_id(shared: dict) -> str:
        events = shared.get("events") or []
        if events:
            return getattr(events[0], "match_id", "match")
        return "match"

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
