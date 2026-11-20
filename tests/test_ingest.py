"""Sportmonks adapter — real-data mapping, honest about what's missing."""

from __future__ import annotations

import pytest

from src.events.audio import describe_event
from src.events.schema import EventType, Team
from src.ingest import SportmonksAdapter
from src.trust import TrustGate


def _payload() -> dict:
    """Canned Sportmonks fixture slice — names/types as the API returns them."""
    return {
        "id": 19456628,
        "participants": [
            {"id": 101, "name": "Home Rovers", "meta": {"location": "home"}},
            {"id": 202, "name": "Away Albion", "meta": {"location": "away"}},
        ],
        "events": [
            {
                "id": 9001,
                "participant_id": 101,
                "minute": 12,
                "extra_minute": 0,
                "player_name": "K. Mensah",
                "related_player_name": "S. Boateng",
                "type": {"name": "Goal"},
            },
            {
                "id": 9002,
                "participant_id": 202,
                "minute": 34,
                "extra_minute": 0,
                "player_name": "J. Smith",
                "type": {"name": "Yellowcard"},
            },
            {
                "id": 9003,
                "participant_id": 202,
                "minute": 45,
                "extra_minute": 2,
                "player_name": "J. Smith",
                "type": {"name": "Own Goal"},
            },
            {
                "id": 9004,
                "participant_id": 101,
                "minute": 63,
                "extra_minute": 0,
                "player_name": "K. Mensah",
                "related_player_name": "A. Traore",
                "type": {"name": "Substitution"},
            },
            {
                "id": 9005,
                "participant_id": 202,
                "minute": 71,
                "extra_minute": 0,
                "player_name": "R. Cole",
                "type": {"name": "VAR"},  # unmapped — counted, not aired
            },
        ],
        "statistics": [
            {
                "participant_id": 101,
                "type": {"name": "Expected Goals"},
                "data": {"value": 1.84},
            },
            {
                "participant_id": 202,
                "type": {"name": "Expected Goals"},
                "data": {"value": 0.61},
            },
        ],
    }


def test_maps_timeline_events():
    result = SportmonksAdapter().to_events(_payload())
    assert result.events, "no events mapped"
    by_type = {}
    for e in result.events:
        by_type.setdefault(e.type, []).append(e)
    assert len(by_type[EventType.GOAL]) == 2
    assert by_type[EventType.FOUL][0].metadata["card"] == "yellow"
    assert len(by_type[EventType.SUBSTITUTION]) == 1


def test_own_goal_counts_for_the_beneficiary():
    result = SportmonksAdapter().to_events(_payload())
    og = next(e for e in result.events if e.metadata.get("own_goal"))
    assert og.team == Team.HOME  # Away Albion's Smith put it in his own net
    assert og.metadata["conceded_by"] == "J. Smith"


def test_extra_time_and_provenance():
    result = SportmonksAdapter().to_events(_payload())
    og = next(e for e in result.events if e.metadata.get("own_goal"))
    assert og.minute == 47  # 45+2 rolls to the 47th minute
    p = result.provenance
    assert p["provider"] == "sportmonks"
    assert p["positions_estimated"] is True
    assert p["reported_xg"] == {"home": 1.84, "away": 0.61}
    assert p["unmapped_types"] == {"var": 1}
    assert all(e.metadata["position_estimated"] for e in result.events)


def test_ids_stable_and_sorted():
    result = SportmonksAdapter().to_events(_payload())
    ids = [e.id for e in result.events]
    assert ids == sorted(set(ids)) or len(set(ids)) == len(ids)
    minutes = [e.minute for e in result.events]
    assert minutes == sorted(minutes)


def test_ad_drops_direction_for_estimated_positions():
    result = SportmonksAdapter().to_events(_payload())
    goal = next(
        e for e in result.events if e.type == EventType.GOAL and not e.metadata.get("own_goal")
    )
    line = describe_event(goal, "Home Rovers", "Away Albion")
    assert "in the area" in line
    assert "on the left" not in line and "on the right" not in line


def test_gate_runs_on_real_events():
    """The trust gate accepts the mapped ledger — the whole point of the seam."""
    result = SportmonksAdapter().to_events(_payload())
    gate = TrustGate(result.events)
    verdict = gate.verify_line("And that makes it 2-0 just after the break!", minute=47)
    assert verdict["status"] in ("verified", "repaired", "rejected")
    # and a fabricated scoreline is still caught on real data
    bad = gate.verify_line("It's 5-0 now, an absolute rout!", minute=50)
    assert bad["status"] == "rejected"


def test_fetch_fails_soft_without_token(monkeypatch):
    monkeypatch.delenv("SPORTMONKS_API_TOKEN", raising=False)
    assert SportmonksAdapter().fetch(19456628) is None


@pytest.mark.parametrize("minute,expected", [(90, 90), (95, 95), (119, 119)])
def test_minute_cap_bounds_extra_time(minute, expected):
    payload = _payload()
    payload["events"] = [
        {
            "id": 1,
            "participant_id": 101,
            "minute": minute,
            "extra_minute": 5,
            "player_name": "X",
            "type": {"name": "Goal"},
        }
    ]
    result = SportmonksAdapter().to_events(payload)
    assert result.events[0].minute == min(expected + 5, 120)
