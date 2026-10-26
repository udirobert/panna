"""Tests for Chalk's reasoning loop on the Microsoft Agent Framework.

Offline by design: the deterministic toolkit, the evidence validator, and the
graceful fallback are exercised without credentials, plus one test that puts
the *real* MAF client on a dead endpoint to prove the failure is contained.
"""

import json

from src.agents.director import DirectorAgent
from src.events.generator import MatchConfig, SyntheticMatchGenerator
from src.foundry.maf import (
    MatchToolkit,
    _parse_json,
    _validate,
    build_toolkit,
    chalk_insights,
)


def _events():
    return SyntheticMatchGenerator(MatchConfig(match_id="match_42", seed=42)).generate()


def test_toolkit_tools_return_grounded_json():
    events = _events()
    by_id = {e.id: e for e in events}
    tk = MatchToolkit(events)

    xg = json.loads(tk.team_xg("Home"))
    assert xg["shots"] > 0
    assert all(eid in by_id for eid in xg["events"])

    ppda = json.loads(tk.team_ppda("Away"))
    assert ppda["ppda"] is None or ppda["ppda"] > 0

    forms = json.loads(tk.formation_breakdown("Home"))
    assert any(f["formation"] in ("4-3-3", "4-4-2", "3-5-2", "4-2-3-1") for f in forms)

    players = json.loads(tk.player_influence("Home"))
    assert len(players) >= 1
    assert all(eid in by_id for p in players for eid in p["events"])

    swing = json.loads(tk.momentum_swing())
    assert "window" in swing
    assert all(eid in by_id for eid in swing.get("events", []))

    window = json.loads(tk.window_events(0, 15, "shot,goal"))
    assert all(e["type"] in ("shot", "goal") for e in window)
    assert all(eid in by_id for eid in (e["id"] for e in window))


def test_maf_tool_schemas_are_derived_from_signatures():
    tools = {t.name: t for t in build_toolkit(_events())}
    assert set(tools) == {
        "team_xg",
        "team_ppda",
        "formation_breakdown",
        "player_influence",
        "momentum_swing",
        "window_events",
    }
    spec = tools["window_events"].to_json_schema_spec()
    params = spec["function"]["parameters"]["properties"]
    assert set(params) == {"start_minute", "end_minute", "kinds"}
    # the model gets typed parameters, not a free-text blob
    assert params["start_minute"]["type"] == "integer"


def test_validation_accepts_only_grounded_claims():
    events = _events()
    by_id = {e.id: e for e in events}
    real = [e.id for e in events if e.type.value in ("shot", "goal")][:3]
    assert len(real) >= 1

    good = _validate(
        _parse_json(
            json.dumps(
                [
                    {
                        "type": "xg_total",
                        "claim": "Home overperformed its xG",
                        "value": 2.8,
                        "confidence": 0.9,
                        "evidence": real,
                    }
                ]
            )
        ),
        by_id,
    )
    assert good and len(good[0]["evidence"]) == 3

    # invented event id -> the whole item is rejected
    assert (
        _validate(
            _parse_json('[{"type":"xg_total","claim":"x","evidence":["evt_99999"]}]'),
            by_id,
        )
        is None
    )
    # no JSON at all -> rejected, not crashed
    assert _validate(_parse_json("the match was great, no data"), by_id) is None
    # markdown fences are tolerated
    payload = json.dumps([{"type": "narrative", "claim": "c", "evidence": [real[0]]}])
    fenced = _validate(_parse_json("```json\n" + payload + "\n```"), by_id)
    assert fenced


def test_offline_chalk_falls_back_to_deterministic_analyst():
    events = _events()
    out = chalk_insights(events, "match_42")
    assert out["source"] == "template"
    assert out["status"] == "fallback"
    assert out["insights"]
    # the core invariant: every cited event id is real
    by_id = {e.id: e for e in events}
    for ins in out["insights"]:
        assert ins.evidence, f"insight {ins.id} has no evidence"
        assert all(eid in by_id for eid in ins.evidence)


def test_director_exposes_reasoning_provenance():
    events = _events()
    result = DirectorAgent().run({"events": events})
    assert result["reasoning_source"] == "template"  # offline env
    assert result["reasoning_model"] is None
    assert result["reasoning_tool_calls"] == 0
    assert result["health"]["analyst"]["status"] in ("healthy", "degraded")


def test_maf_client_failure_falls_back_gracefully(monkeypatch):
    """Point the *real* MAF stack at a dead endpoint: the loop must contain
    the failure, record it, and return deterministic insights."""
    from src.foundry import client as client_mod

    monkeypatch.setenv("FOUNDRY_ENDPOINT", "https://127.0.0.1:9/openai")
    monkeypatch.setenv("FOUNDRY_API_KEY", "test-key-not-real")
    monkeypatch.setenv("FOUNDRY_DEPLOYMENT", "gpt-5.4")
    monkeypatch.setattr(client_mod, "_client", None)  # rebuild the singleton
    try:
        out = chalk_insights(_events(), "match_dead", timeout=30)
    finally:
        monkeypatch.delenv("FOUNDRY_ENDPOINT", raising=False)
        monkeypatch.delenv("FOUNDRY_API_KEY", raising=False)
        monkeypatch.setattr(client_mod, "_client", None)

    assert out["source"] == "template"  # degraded, not broken
    assert out["status"] == "fallback"
    assert out["insights"], "fallback must still produce the board"
    assert out["error"], "the failure should be visible in the trace"

    # the span captured the attempt
    from src.foundry.tracing import spans_for

    chalk_spans = [s for s in spans_for("match_dead") if s.agent == "analyst"]
    assert chalk_spans and chalk_spans[-1].status == "fallback"
    assert "chalk.analyze" in chalk_spans[-1].operation
