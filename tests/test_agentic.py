"""Tests for the Foundry-backed narrative agents + tracing (offline stub path)."""

from fastapi.testclient import TestClient

from src.agents.director import DirectorAgent
from src.api.main import app
from src.events.generator import MatchConfig, SyntheticMatchGenerator
from src.foundry import narrative
from src.foundry.tracing import spans_for, summary_for


def test_director_exposes_commentary_source():
    events = SyntheticMatchGenerator(MatchConfig(seed=1)).generate()
    result = DirectorAgent().run({"events": events})
    # offline (no FOUNDRY_* creds) => deterministic template source
    assert result["commentary_source"] in ("template", "foundry")
    assert isinstance(result["commentary"], list)
    assert result["health"]["commentator"]["status"] == "healthy"


def test_booth_offline_falls_back_to_template_and_traces():
    events = SyntheticMatchGenerator(MatchConfig(seed=2)).generate()
    km = list(DirectorAgent().run({"events": events})["key_moments"])
    out = narrative.booth_commentary("match_001", {"key_moments": km, "insights": []})
    # without credentials the Booth degrades to the deterministic commentator
    assert out["source"] == "template"
    assert out["status"] in ("ok", "fallback")
    # a span was recorded for the booth agent
    spans = spans_for("match_001")
    assert any(s.agent == "booth" for s in spans)


def test_verdict_offline_and_traced():
    events = SyntheticMatchGenerator(MatchConfig(seed=3)).generate()
    result = DirectorAgent().run({"events": events})
    out = narrative.verdict_recap("match_001", result["insights"], result["key_moments"])
    assert isinstance(out["result"], str)
    assert out["result"].strip()
    assert any(s.agent == "chalk-verdict" for s in spans_for("match_001"))


def test_health_reports_foundry_state():
    c = TestClient(app)
    body = c.get("/health").json()
    assert body["status"] == "ok"
    assert "foundry" in body
    assert "available" in body["foundry"]
    assert "deployment" in body["foundry"]


def test_agentic_narrate_and_tracing_endpoints():
    c = TestClient(app)
    c.post("/matches/generate?match_id=ag1&seed=4")
    r = c.get("/agentic/narrate/ag1")
    assert r.status_code == 200
    body = r.json()
    assert "commentary" in body
    assert body["source"] in ("template", "foundry")

    tr = c.get("/agentic/tracing/ag1")
    assert tr.status_code == 200
    assert tr.json()["span_count"] >= 0
    trd = c.get("/agentic/tracing/ag1?detail=true")
    assert "spans" in trd.json()


def test_summary_counts_foundry_vs_fallback():
    narrative.booth_commentary("sum1", {"key_moments": [], "insights": []})
    narrative.verdict_recap("sum1", [], [])
    s = summary_for("sum1")
    assert s["span_count"] >= 2
    # offline: everything is the template fallback
    assert s["foundry_calls"] == 0
    assert s["fallback_calls"] + s["errors"] >= 2
