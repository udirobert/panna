"""Tests for the viral primitives: deterministic match resolve + share poster."""

from fastapi.testclient import TestClient

from src.api.main import app


def test_resolve_creates_and_reports_seed():
    c = TestClient(app)
    r = c.get("/matches/resolve/match_137")
    assert r.status_code == 200
    body = r.json()
    # seed is derived from the match id — the URL is the match
    assert body["seed"] == 137
    assert body["match_id"] == "match_137"
    assert body["event_count"] > 0

    # idempotent: same match, same identity
    again = c.get("/matches/resolve/match_137").json()
    assert again["seed"] == body["seed"]
    assert again["event_count"] == body["event_count"]


def test_resolve_default_seed_for_non_numeric_id():
    c = TestClient(app)
    body = c.get("/matches/resolve/custom_fixture").json()
    assert body["seed"] == 42
    assert body["event_count"] > 0


def test_share_poster_renders_self_contained_html():
    c = TestClient(app)
    c.post("/matches/generate?match_id=share_1&seed=9")
    r = c.get("/share/share_1")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    doc = r.text
    assert "REPLAY THIS MATCH" in doc
    assert "CASE FILED" in doc
    assert "match_001" not in doc
    # replay link carries the match id and points at the frontend
    assert "/?match=share_1" in doc
    assert "http://localhost:3000" in doc


def test_share_404_for_unknown_match():
    c = TestClient(app)
    r = c.get("/share/never_generated")
    assert r.status_code == 404


def test_recap_structured_exhibits():
    c = TestClient(app)
    c.post("/matches/generate?match_id=recap_1&seed=7")
    body = c.get("/recap/recap_1").json()
    assert body["source"] in ("template", "foundry")
    structured = body["structured"]
    assert structured["score"]["home"] >= 0
    assert isinstance(structured["xg"]["home"], float)
    assert isinstance(structured["exhibits"], list)
    for ex in structured["exhibits"]:
        assert "claim" in ex and "confidence" in ex and "evidence" in ex

    # formation timeline: kickoff formations from config + evolution events
    formations = structured["formations"]
    assert formations["kickoff"]["home"] == "4-3-3"
    assert formations["kickoff"]["away"] == "4-4-2"
    assert "home" in formations["final"] and "away" in formations["final"]
    assert isinstance(formations["evolution"], list)
