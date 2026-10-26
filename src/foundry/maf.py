"""Chalk's reasoning loop on the Microsoft Agent Framework (MAF).

This is where "agentic" becomes literal: when Foundry credentials are
configured, the Analyst's reasoning is an MAF agent (an
``agent_framework.Agent`` on Azure OpenAI) that is handed the match as a
read-only **toolkit** — functions computed from the deterministic models —
and writes insights as JSON that must cite *real* event ids. Every number in
a claim is something the model looked up; every insight is re-validated
against the event ledger before it reaches the board.

Without credentials, a deterministic analyst produces the identical Insight
shape, so the UI, tests, and demo never depend on the network. Either way a
span is recorded (see src/foundry/tracing.py) — the governance panel shows
which path ran, and the MAF loop is observable, not asserted.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from typing import Any

from src.events.schema import Event, Insight
from src.foundry.tracing import record_span

INSTRUCTIONS = """You are CHALK, the tactical analyst in the Panna match-intelligence system.
You read the match strictly through your toolkit — every number in a claim must
come from a tool result. Then file your 3 to 6 sharpest insights.

Respond with ONLY a JSON array. Each item:
{"type": "xg_total|pressing_intensity|formation_effectiveness|player_influence"
           "|momentum_shift|narrative",
 "claim": "one specific sentence with concrete numbers",
 "value": <number>,
 "confidence": <0.0 to 1.0>,
 "evidence": ["<event id>", ... up to 8 real event ids supporting the claim]}

Rules:
- Cite only event ids that appeared in a tool result. No invented ids.
- Prefer the two or three findings a pundit would get wrong over a recitation
  of every stat (e.g. a team underperforming its xG, a formation that failed).
- No prose, markdown, or code fences before or after the JSON array.
"""


# ---- toolkit: the match as read-only tools --------------------------------


class MatchToolkit:
    """The match, exposed as typed read-only functions the model can call.

    Each method's signature is what MAF turns into the JSON schema, so the
    parameter names and types below are the model's API surface.
    """

    def __init__(self, events: list[Event]) -> None:
        from src.models.formation import formation_effectiveness
        from src.models.influence import player_influence as player_influence_fn
        from src.models.momentum import momentum
        from src.models.pressing import ppda
        from src.models.xg import event_xg

        self._events = events
        self._formation_effectiveness = formation_effectiveness
        self._player_influence = player_influence_fn
        self._momentum = momentum
        self._ppda = ppda
        self._event_xg = event_xg

    def team_xg(self, team: str) -> str:
        """Expected goals for one team: shots taken, total xG, goals scored,
        the single best chance, and the event ids of the chances.
        team is 'Home' or 'Away'."""
        out = {"shots": 0, "xg": 0.0, "goals": 0, "best_xg": 0.0, "events": []}
        for e in self._events:
            if e.type.value not in ("shot", "goal") or e.team.value != team:
                continue
            xg = self._event_xg(e) or float(e.metadata.get("xg", 0.0))
            out["shots"] += 1
            out["xg"] = round(out["xg"] + xg, 3)
            if e.type.value == "goal":
                out["goals"] += 1
            out["best_xg"] = max(out["best_xg"], xg)
            if len(out["events"]) < 8:
                out["events"].append(e.id)
        out["xg"] = round(out["xg"], 3)
        return json.dumps(out)

    def team_ppda(self, team: str) -> str:
        """Passes per defensive action (PPDA) for one team. Lower means more
        pressing. team is 'Home' or 'Away'."""
        p = self._ppda(self._events, _team(team))
        return json.dumps(
            {"ppda": p if p != float("inf") else None, "note": "lower = more pressing"}
        )

    def formation_breakdown(self, team: str) -> str:
        """Shots and xG per formation a team used, with minutes in each shape.
        team is 'Home' or 'Away'."""
        fe = self._formation_effectiveness(self._events, _team(team))
        return json.dumps(
            [
                {
                    "formation": f,
                    "minutes": s["minutes"],
                    "shots": s["shots"],
                    "xg": s["xg"],
                }
                for f, s in fe.items()
            ]
        )

    def player_influence(self, team: str) -> str:
        """Top three most influential players for a team, with the event ids
        behind the ranking. team is 'Home' or 'Away'."""
        ranked = self._player_influence(self._events, _team(team))[:3]
        return json.dumps(
            [
                {
                    "player": t["player"],
                    "influence": t["influence"],
                    "events": [e.id for e in self._events if e.player == t["player"]][:5],
                }
                for t in ranked
            ]
        )

    def momentum_swing(self) -> str:
        """The biggest momentum swing in the match: the minute window, the xG
        swing, and the shot/goal event ids inside that window."""
        mom = self._momentum(self._events)
        if not mom:
            return json.dumps({"swing": None})
        biggest = max(mom, key=lambda m: abs(m["momentum"]))
        lo, hi = _window_minutes(biggest["window"])
        evs = [
            e.id
            for e in self._events
            if lo is not None and lo <= e.minute < hi and e.type.value in ("shot", "goal")
        ]
        return json.dumps(
            {"window": biggest["window"], "swing": biggest["momentum"], "events": evs[:8]}
        )

    def window_events(self, start_minute: int, end_minute: int, kinds: str) -> str:
        """Events in a minute range [start_minute, end_minute), filtered by
        type. kinds is a comma separated subset of: shot, goal, tackle, foul,
        set_piece, pass, possession_change. Returns up to 10 events with ids,
        minute, team, player and xG — the evidence miner for any claim."""
        wanted = {k.strip() for k in kinds.split(",") if k.strip()}
        out = []
        for e in self._events:
            if e.type.value not in wanted or not (start_minute <= e.minute < end_minute):
                continue
            out.append(
                {
                    "id": e.id,
                    "minute": e.minute,
                    "type": e.type.value,
                    "team": e.team.value,
                    "player": e.player,
                    "xg": e.metadata.get("xg"),
                }
            )
            if len(out) >= 10:
                break
        return json.dumps(out)


def _team(value: str) -> Any:
    from src.events.schema import Team

    return Team.HOME if value.lower() == "home" else Team.AWAY


def _window_minutes(window: str) -> tuple[int | None, int | None]:
    parts = [p.strip().rstrip("'") for p in window.replace("–", "-").split("-")]
    parts = [p for p in parts if p.isdigit()]
    if len(parts) == 2:
        return int(parts[0]), int(parts[1])
    return None, None


def build_toolkit(events: list[Event]):
    """The match toolkit as MAF FunctionTools (one per toolkit method)."""
    from agent_framework import tool

    toolkit = MatchToolkit(events)
    return [
        tool(getattr(toolkit, name), name=name, description=doc)
        for name, doc in (
            ("team_xg", "Expected goals for a team, with the chance event ids."),
            ("team_ppda", "Pressing intensity (PPDA) for a team."),
            ("formation_breakdown", "Per-formation shots and xG for a team."),
            ("player_influence", "Top three influential players for a team."),
            ("momentum_swing", "The biggest xG momentum swing and its events."),
            ("window_events", "Ground an event in a minute window by type."),
        )
    ]


def toolkit_tool_calls(tools) -> int:
    """Count how many times the model invoked the toolkit (MAF tracks it)."""
    return sum(getattr(t, "invocation_count", 0) for t in tools)


# ---- validation: the board only shows grounded claims ---------------------

_TYPES = {
    "xg_total",
    "pressing_intensity",
    "formation_effectiveness",
    "player_influence",
    "momentum_shift",
    "narrative",
    "key_moment",
}


def _parse_json(raw: str) -> Any:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # tolerate a single array buried in surrounding prose
        start, end = raw.find("["), raw.rfind("]")
        if start != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def _validate(payload: Any, by_id: dict[str, Event]) -> list[dict] | None:
    """Accept a JSON array of insight dicts; drop anything ungrounded."""
    if isinstance(payload, dict) and isinstance(payload.get("insights"), list):
        payload = payload["insights"]
    if not isinstance(payload, list):
        return None
    out: list[dict] = []
    for item in payload[:6]:
        if not isinstance(item, dict):
            continue
        claim = str(item.get("claim", "")).strip()
        etype = str(item.get("type", "")).strip() or "narrative"
        evidence = [
            str(e)
            for e in (item.get("evidence") or [])
            if isinstance(e, str | int) and str(e) in by_id
        ][:8]
        if not claim or len(evidence) < 1:
            continue  # no claim, or no grounding -> reject
        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.6))))
        except (TypeError, ValueError):
            confidence = 0.6
        value = item.get("value", confidence)
        if not isinstance(value, int | float | str):
            value = confidence
        out.append(
            {
                "type": etype if etype in _TYPES else "narrative",
                "claim": claim[:300],
                "value": value,
                "confidence": confidence,
                "evidence": evidence,
            }
        )
    return out or None


def _to_insights(candidates: list[dict]) -> list[Insight]:
    return [
        Insight(
            id=f"ins_maf_{i:02d}_{uuid.uuid4().hex[:4]}",
            type=c["type"],
            claim=c["claim"],
            value=c["value"],
            confidence=c["confidence"],
            evidence=c["evidence"],
            agent="chalk-maf",
            timestamp="0:00",
        )
        for i, c in enumerate(candidates)
    ]


# ---- async bridge: one worker loop for sync and async callers -------------

_LOOP: asyncio.AbstractEventLoop | None = None
_LOOP_LOCK = threading.Lock()


def _ensure_loop() -> asyncio.AbstractEventLoop:
    global _LOOP
    if _LOOP is None or not _LOOP.is_running():
        with _LOOP_LOCK:
            if _LOOP is None or not _LOOP.is_running():
                _LOOP = asyncio.new_event_loop()
                threading.Thread(
                    target=_LOOP.run_forever, daemon=True, name="panna-maf-loop"
                ).start()
    return _LOOP


def _run_async(coro: Any, timeout: float) -> Any:
    future = asyncio.run_coroutine_threadsafe(coro, _ensure_loop())
    return future.result(timeout=timeout)


def _maf_client() -> tuple[Any, str | None]:
    """Build an MAF chat client on the Foundry deployment, or (None, None)."""
    from src.foundry.client import get_client

    fc = get_client()
    if not fc.available:
        return None, None
    try:
        from agent_framework.openai import OpenAIChatClient

        client = OpenAIChatClient(
            model=fc.deployment,
            api_key=fc.api_key,
            azure_endpoint=fc.endpoint,
            api_version=fc.api_version,
        )
        return client, fc.deployment
    except Exception:  # noqa: BLE001
        return None, None


# ---- the loop ---------------------------------------------------------------


def chalk_insights(events: list[Event], match_id: str, timeout: float = 60.0) -> dict:
    """Run Chalk's reasoning. MAF tool loop when Foundry is configured,
    deterministic analyst otherwise. Always returns validated Insights."""
    from src.agents.analyst import AnalystAgent

    started = time.perf_counter()
    client, model = _maf_client()
    insights: list[Insight] | None = None
    source = "template"
    status = "fallback"
    error: str | None = None
    tool_calls = 0

    if client is not None:
        try:
            from agent_framework import Agent

            tools = build_toolkit(events)
            agent = Agent(
                client,
                instructions=INSTRUCTIONS,
                name="chalk",
                id="chalk-maf",
                tools=tools,
            )
            response = _run_async(
                agent.run(f"Match {match_id}. Read the match, file your findings."), timeout
            )
            candidates = _validate(_parse_json(response.text or ""), {e.id: e for e in events})
            if candidates:
                insights = _to_insights(candidates)
                source, status, tool_calls = "foundry", "ok", toolkit_tool_calls(tools)
            else:
                error = "MAF reply contained no grounded insights"
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {str(exc)[:140]}"

    if insights is None:
        insights = AnalystAgent().run({"events": events})

    record_span(
        match_id=match_id,
        agent="analyst",
        operation="chalk.analyze",
        source=source,
        model=model,
        status=status,
        duration_ms=(time.perf_counter() - started) * 1000,
        error=error,
    )
    return {
        "insights": insights,
        "source": source,
        "status": status,
        "model": model,
        "tool_calls": tool_calls,
        "error": error,
    }
