"""Producer gate tests: rejected lines stay off air until a human clears them."""

import pytest

from src.api.session import get_or_create_session
from src.events.generator import MatchConfig, SyntheticMatchGenerator


@pytest.fixture()
def session():
    events = SyntheticMatchGenerator(MatchConfig(match_id="prod_1", seed=9)).generate()
    return get_or_create_session("prod_1", events, seed=9)


def test_rejected_items_are_held_off_air(session):
    session.clock = 5400.0  # full time
    session._cursor = len(session.timeline)  # noqa: SLF001
    snap = session.snapshot()
    # everything rejected by the verifier appears in `held`, not the feed
    for ins in snap["insights"]:
        v = ins.get("verification") or {}
        assert v.get("status") != "rejected"
    for c in snap["commentary"]:
        v = c.get("verification") or {}
        assert v.get("status") != "rejected"
    for h in snap["held"]:
        v = h.get("verification") or {}
        assert v.get("status") == "rejected"


def test_approve_airs_held_line(session):
    bad = session.seed_bad_claim()
    session.seek(session.clock + 10)  # move the broadcast clock past the plant
    snap = session.snapshot()
    held_ids = {h["id"] for h in snap["held"]}
    planted_id = next(iter(bad["verdicts"]))
    assert planted_id in held_ids

    session.decide(planted_id, "approve")
    snap = session.snapshot()
    assert planted_id not in {h["id"] for h in snap["held"]}


def test_kill_removes_line(session):
    bad = session.seed_bad_claim()
    session.seek(session.clock + 10)
    planted_id = next(iter(bad["verdicts"]))
    session.decide(planted_id, "kill")
    snap = session.snapshot()
    assert planted_id not in {h["id"] for h in snap["held"]}
    board = {r["id"]: r["air_status"] for r in session.board()}
    assert board[planted_id] == "killed"


def test_viewer_cost_guard(session):
    session.viewers = 0
    session.play()
    session.add_viewer()
    assert session.viewers == 1
    session.remove_viewer()
    # nobody watching → the matchday pauses
    assert session.auto_paused
    assert not session.playing
    session.add_viewer()
    assert session.playing and not session.auto_paused


def test_seed_bad_claim_lands_in_hold(session):
    out = session.seed_bad_claim()
    assert len(out["planted"]) == 2
    assert all(v["status"] == "rejected" for v in out["verdicts"].values())
    session.seek(session.clock + 10)
    held_ids = {h["id"] for h in session.snapshot()["held"]}
    assert set(out["verdicts"]) <= held_ids
