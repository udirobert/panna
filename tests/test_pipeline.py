from fastapi.testclient import TestClient

from src.agents.director import DirectorAgent
from src.api.main import app
from src.events.generator import MatchConfig, SyntheticMatchGenerator


def test_generator_deterministic():
    a = SyntheticMatchGenerator(MatchConfig(seed=7)).generate()
    b = SyntheticMatchGenerator(MatchConfig(seed=7)).generate()
    assert len(a) == len(b)
    assert a[0].id == b[0].id


def test_director_runs():
    events = SyntheticMatchGenerator(MatchConfig(seed=1)).generate()
    result = DirectorAgent().run({"events": events})
    assert result["health"]["scout"]["status"] == "healthy"
    assert len(result["insights"]) > 0
    assert len(result["key_moments"]) > 0


def test_api_flow():
    c = TestClient(app)
    r = c.post("/matches/generate?match_id=t&seed=2")
    assert r.status_code == 200
    assert r.json()["event_count"] > 0
    assert c.get("/insights/t").status_code == 200
    assert c.get("/recap/t").status_code == 200
    assert c.get("/health").json()["status"] == "ok"
