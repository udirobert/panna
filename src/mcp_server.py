"""Panna as an MCP server — the match, queryable by any MCP client.

This is the interoperability story made concrete: the same six-function
toolkit Chalk uses inside the Microsoft Agent Framework is exposed over the
Model Context Protocol, so any MCP-compatible client (Copilot, Claude
Desktop, a custom agent) can query a match — and, thanks to seed
determinism, *any* match: ``match_info("match_137")`` regenerates it.

Run locally:
    panna-mcp                     # stdio transport
or from Python:
    python -m src.mcp_server

Tools are synchronous reads over the deterministic pipeline; no Foundry
credentials are required (insights come from the deterministic analyst,
with the MAF reasoning loop kicking in automatically when configured).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from src.events.frames import event_frame
from src.events.generator import MatchConfig, SyntheticMatchGenerator

_MATCHES: dict[str, list] = {}
_CONFIGS: dict[str, MatchConfig] = {}


def _load(match_id: str) -> tuple[MatchConfig, list]:
    """Get or deterministically regenerate a match (the URL-is-the-match rule)."""
    cfg = _CONFIGS.get(match_id)
    if cfg is None:
        seed = 42
        if match_id.startswith("match_") and match_id[6:].isdigit():
            seed = int(match_id[6:])
        cfg = MatchConfig(match_id=match_id, seed=seed)
        _CONFIGS[match_id] = cfg
    if match_id not in _MATCHES:
        _MATCHES[match_id] = SyntheticMatchGenerator(cfg).generate()
    return cfg, _MATCHES[match_id]


def _score(events: list) -> tuple[int, int]:
    home = away = 0
    for e in events:
        if e.type.value == "goal":
            if e.team.value == "Home":
                home += 1
            else:
                away += 1
    return home, away


def _xg(events: list) -> tuple[float, float]:
    from src.models.xg import event_xg

    h = a = 0.0
    for e in events:
        if e.type.value in ("shot", "goal"):
            xg = event_xg(e) or float(e.metadata.get("xg", 0.0))
            if e.team.value == "Home":
                h += xg
            else:
                a += xg
    return round(h, 2), round(a, 2)


# ---- tools -----------------------------------------------------------------


def _tool_match_info() -> dict:
    cfg, events = _load(_arg("match_id"))
    h, a = _score(events)
    hx, ax = _xg(events)
    return {
        "match_id": cfg.match_id,
        "seed": cfg.seed,
        "home_team": cfg.home_team,
        "away_team": cfg.away_team,
        "score": {"home": h, "away": a},
        "xg": {"home": hx, "away": ax},
        "event_count": len(events),
        "note": "Matches are deterministic per seed: any client can regenerate this exact match.",
    }


def _tool_match_events() -> dict:
    offset = int(_arg("offset", 0))
    limit = min(int(_arg("limit", 100)), 500)
    _, events = _load(_arg("match_id"))
    chunk = events[offset : offset + limit]
    return {
        "match_id": _arg("match_id"),
        "total": len(events),
        "offset": offset,
        "events": [event_frame(e) for e in chunk],
    }


def _tool_team_summary() -> dict:
    from src.models.formation import formation_effectiveness
    from src.models.influence import player_influence
    from src.models.pressing import ppda
    from src.models.xg import event_xg

    team = _arg("team", "Home")
    _, events = _load(_arg("match_id"))
    team_val = "Home" if str(team).lower().startswith("h") else "Away"
    from src.events.schema import Team

    t = Team.HOME if team_val == "Home" else Team.AWAY
    xg = shots = 0.0
    for e in events:
        if e.type.value in ("shot", "goal") and e.team.value == team_val:
            shots += 1
            xg += event_xg(e) or float(e.metadata.get("xg", 0.0))
    p = ppda(events, t)
    fe = formation_effectiveness(events, t)
    ranked = player_influence(events, t)[:3]
    return {
        "team": team_val,
        "shots": shots,
        "xg": round(xg, 2),
        "ppda": p if p != float("inf") else None,
        "formations": [
            {"formation": f, "minutes": s["minutes"], "shots": s["shots"], "xg": s["xg"]}
            for f, s in fe.items()
        ],
        "top_players": ranked,
    }


def _tool_match_insights() -> dict:
    from src.agents.analyst import AnalystAgent

    _, events = _load(_arg("match_id"))
    insights = AnalystAgent().run({"events": events})
    return {
        "match_id": _arg("match_id"),
        "insights": [i.model_dump() for i in insights],
    }


def _tool_event_details() -> dict:
    ids = _arg("event_ids", [])
    if isinstance(ids, str):
        ids = [x.strip() for x in ids.split(",") if x.strip()]
    _, events = _load(_arg("match_id"))
    by_id = {e.id: e for e in events}
    out = []
    for eid in ids:
        e = by_id.get(str(eid))
        if e is not None:
            out.append(event_frame(e))
    return {"requested": list(ids), "found": out}


def _arg(name: str, default: Any = None) -> Any:
    """Read the current call's arguments (set by the on_call_tool handler)."""
    return _ARGS.get(name, default)


_ARGS: dict[str, Any] = {}

_TOOLS: list[types.Tool] = [
    types.Tool(
        name="match_info",
        description=(
            "Look up a match by id (match_<seed>). Regenerates it deterministically "
            "if needed. Returns seed, teams, score, xG."
        ),
        input_schema={
            "type": "object",
            "properties": {"match_id": {"type": "string", "description": "e.g. match_137"}},
            "required": ["match_id"],
        },
    ),
    types.Tool(
        name="match_events",
        description=(
            "Page through the match's event ledger in the canonical flat frame "
            "(StatsBomb-like: id, type, team, minute, x/y, xg)."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "match_id": {"type": "string"},
                "offset": {"type": "integer", "default": 0},
                "limit": {"type": "integer", "default": 100, "maximum": 500},
            },
            "required": ["match_id"],
        },
    ),
    types.Tool(
        name="team_summary",
        description=(
            "Tactical summary for one team: shots, total xG, PPDA (lower = more "
            "pressing), per-formation stats, top three players."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "match_id": {"type": "string"},
                "team": {"type": "string", "enum": ["Home", "Away"], "default": "Home"},
            },
            "required": ["match_id"],
        },
    ),
    types.Tool(
        name="match_insights",
        description=(
            "The analyst's insights with evidence: every insight carries the event "
            "ids that ground it (the explainability contract)."
        ),
        input_schema={
            "type": "object",
            "properties": {"match_id": {"type": "string"}},
            "required": ["match_id"],
        },
    ),
    types.Tool(
        name="event_details",
        description=(
            "Fetch specific events by id — the grounding step for verifying any "
            "insight's evidence."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "match_id": {"type": "string"},
                "event_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["match_id", "event_ids"],
        },
    ),
]


def _handler_for(name: str) -> Any:
    return {
        "match_info": _tool_match_info,
        "match_events": _tool_match_events,
        "team_summary": _tool_team_summary,
        "match_insights": _tool_match_insights,
        "event_details": _tool_event_details,
    }.get(name)


async def _on_list_tools(ctx: Any, params: Any) -> types.ListToolsResult:
    return types.ListToolsResult(tools=_TOOLS)


async def _on_call_tool(ctx: Any, params: Any) -> types.CallToolResult:
    global _ARGS
    _ARGS = dict(getattr(params, "arguments", None) or {})
    handler = _handler_for(params.name)
    if handler is None:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"unknown tool: {params.name}")],
            is_error=True,
        )
    try:
        result = handler()
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(result))]
        )
    except Exception as exc:  # noqa: BLE001
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"{type(exc).__name__}: {exc}")],
            is_error=True,
        )
    finally:
        _ARGS = {}


def build_server() -> Server:
    return Server(
        "panna",
        instructions=(
            "Query a deterministic synthetic football match: stats, events, and "
            "grounded insights."
        ),
        on_list_tools=_on_list_tools,
        on_call_tool=_on_call_tool,
    )


async def _amain() -> None:
    async with stdio_server() as (read, write):
        server = build_server()
        await server.run(read, write, server.create_initialization_options())


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
