"""POST /matches/ingest — real provider data enters the broadcast pipeline."""

from __future__ import annotations

from fastapi.testclient import TestClient

import src.api.routes.matches as matches
from src.api.main import app
from src.events.schema import Event, EventType, Position, Team
from src.ingest import IngestResult

c = TestClient(app)


def _fake_result() -> IngestResult:
    ev = Event(
        id="sb_1_0000",
        match_id="sb_1",
        minute=10,
        second=0,
        type=EventType.GOAL,
        player="T. Striker",
        team=Team.HOME,
        position=Position(x=105.0, y=40.0),
        outcome="goal",
        metadata={"source": "statsbomb-open-data"},
    )
    return IngestResult(
        events=[ev],
        provenance={
            "provider": "statsbomb-open-data",
            "match_id": "1",
            "home_team": "Real Home",
            "away_team": "Real Away",
            "events_mapped": 1,
            "events_skipped": 0,
        },
    )


def test_resolve_real_id_requires_ingest():
    r = c.get("/matches/resolve/sb_999999")
    assert r.status_code == 404
    assert "ingest" in r.json()["detail"]


def test_ingest_then_resolve(monkeypatch):
    monkeypatch.setattr(
        "src.ingest.statsbomb.StatsBombAdapter.fetch", lambda *a, **k: _fake_result()
    )
    r = c.post(
        "/matches/ingest",
        json={"provider": "statsbomb", "match_id": "1", "competition_id": 43, "season_id": 3},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["match_id"] == "sb_1"
    assert body["provenance"]["provider"] == "statsbomb-open-data"

    r2 = c.get("/matches/resolve/sb_1")
    assert r2.status_code == 200
    data = r2.json()
    assert data["home_team"] == "Real Home"
    assert data["away_team"] == "Real Away"
    assert data["data_source"]["provider"] == "statsbomb-open-data"


def test_ingest_fetch_failure_is_502(monkeypatch):
    monkeypatch.setattr("src.ingest.statsbomb.StatsBombAdapter.fetch", lambda *a, **k: None)
    r = c.post("/matches/ingest", json={"provider": "statsbomb", "match_id": "404"})
    assert r.status_code == 502


def test_synthetic_resolve_still_works():
    matches._CONFIGS.pop("match_t9", None)
    matches._MATCHES.pop("match_t9", None)
    r = c.get("/matches/resolve/match_t9")
    assert r.status_code == 200
    assert r.json()["data_source"] == "synthetic"
