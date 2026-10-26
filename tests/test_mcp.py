"""Tests for the MCP server: the match toolkit exposed over the Model Context
Protocol. Exercises the real list/call handlers with MCP protocol types, so
the interop surface is tested, not asserted."""

import asyncio
import json

from mcp import types

from src.mcp_server import _on_call_tool, _on_list_tools, build_server


def _call(name: str, **args) -> dict:
    params = types.CallToolRequestParams(name=name, arguments=args)
    result = asyncio.run(_on_call_tool(None, params))
    assert result.is_error is not True, f"{name} errored: {result.content[0].text}"
    return json.loads(result.content[0].text)


def test_server_exposes_the_toolkit():
    tools = asyncio.run(_on_list_tools(None, None))
    names = {t.name for t in tools.tools}
    assert names == {
        "match_info",
        "match_events",
        "team_summary",
        "match_insights",
        "event_details",
    }
    for t in tools.tools:
        # every tool carries a schema a client can render
        assert t.input_schema["type"] == "object"


def test_match_info_regenerates_by_seed():
    out = _call("match_info", match_id="match_137")
    assert out["seed"] == 137
    assert out["event_count"] > 0
    assert "score" in out and "xg" in out


def test_match_events_use_canonical_flat_frame():
    out = _call("match_events", match_id="match_42", limit=10)
    assert out["total"] > 10
    ev = out["events"][0]
    # flat, not nested: the interop contract
    for key in ("id", "type", "team", "minute", "x", "y"):
        assert key in ev
    assert "position" not in ev and "end_location" not in ev


def test_team_summary_and_insights_are_grounded():
    summary = _call("team_summary", match_id="match_42", team="Home")
    assert summary["shots"] >= 0
    assert isinstance(summary["formations"], list)
    assert len(summary["top_players"]) >= 1

    ins = _call("match_insights", match_id="match_42")
    events = _call("match_events", match_id="match_42", limit=500)
    by_id = {e["id"] for e in events["events"]}
    for i in ins["insights"]:
        assert i["evidence"], f"insight {i['id']} is ungrounded"
        assert all(eid in by_id for eid in i["evidence"])


def test_event_details_fetches_by_id():
    events = _call("match_events", match_id="match_42", limit=5)
    ids = [e["id"] for e in events["events"]]
    out = _call("event_details", match_id="match_42", event_ids=ids)
    assert len(out["found"]) == len(ids)
    assert {e["id"] for e in out["found"]} == set(ids)


def test_unknown_tool_reports_error():
    params = types.CallToolRequestParams(name="nope", arguments={})
    result = asyncio.run(_on_call_tool(None, params))
    assert result.is_error


def test_server_constructs():
    server = build_server()
    assert server.name == "panna"
