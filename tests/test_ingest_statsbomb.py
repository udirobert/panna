"""StatsBomb open-data adapter — real event-level data, measured not estimated."""

from __future__ import annotations

from src.events.audio import describe_event
from src.events.schema import EventType, Team
from src.ingest import StatsBombAdapter
from src.trust import TrustGate


def _events() -> list[dict]:
    """Canned StatsBomb slice — field shapes as events/*.json returns them."""
    return [
        {
            "id": "aaa1",
            "index": 1,
            "period": 1,
            "timestamp": "00:17:56.987",
            "minute": 17,
            "second": 56,
            "type": {"id": 20, "name": "Own Goal For"},
            "team": {"id": 1, "name": "Home XI"},
        },
        {
            "id": "aaa2",
            "index": 2,
            "period": 1,
            "timestamp": "00:17:56.987",
            "minute": 17,
            "second": 56,
            "type": {"id": 25, "name": "Own Goal Against"},
            "team": {"id": 2, "name": "Away XI"},
            "player": {"id": 99, "name": "M. Ownnet"},
        },
        {
            "id": "bbb1",
            "index": 40,
            "period": 1,
            "timestamp": "00:27:53.0",
            "minute": 27,
            "second": 53,
            "type": {"id": 16, "name": "Shot"},
            "team": {"id": 2, "name": "Away XI"},
            "player": {"id": 55, "name": "W. Winger"},
            "location": [110.5, 35.0],
            "shot": {
                "statsbomb_xg": 0.084,
                "outcome": {"name": "Goal"},
                "type": {"name": "Open Play"},
                "body_part": {"name": "Left Foot"},
                "key_pass_id": "ccc1",
            },
        },
        {
            "id": "ccc1",
            "index": 39,
            "period": 1,
            "timestamp": "00:27:51.0",
            "minute": 27,
            "second": 51,
            "type": {"id": 30, "name": "Pass"},
            "team": {"id": 2, "name": "Away XI"},
            "player": {"id": 56, "name": "A. Creator"},
            "location": [95.0, 30.0],
            "pass": {"end_location": [110.0, 35.0], "type": {"name": "Cross"}},
        },
        {
            "id": "ddd1",
            "index": 60,
            "period": 1,
            "timestamp": "00:33:10.0",
            "minute": 33,
            "second": 10,
            "type": {"id": 4, "name": "Foul Committed"},
            "team": {"id": 1, "name": "Home XI"},
            "player": {"id": 77, "name": "H. Tackler"},
            "location": [70.0, 40.0],
            "foul_committed": {"card": {"name": "Yellow Card"}},
        },
        {
            "id": "eee1",
            "index": 100,
            "period": 2,
            "timestamp": "00:61:00.0",
            "minute": 61,
            "second": 0,
            "type": {"id": 19, "name": "Substitution"},
            "team": {"id": 1, "name": "Home XI"},
            "player": {"id": 78, "name": "T. Off"},
            "substitution": {"replacement": {"name": "F. On"}},
        },
        {
            "id": "fff1",
            "index": 150,
            "period": 2,
            "timestamp": "00:70:12.0",
            "minute": 70,
            "second": 12,
            "type": {"id": 23, "name": "Goal Keeper"},
            "team": {"id": 2, "name": "Away XI"},
            "player": {"id": 90, "name": "K. Keeper"},
            "location": [5.0, 40.0],
        },
    ]


def test_own_goal_pair_collapses_to_beneficiary():
    r = StatsBombAdapter().to_events(_events(), "Home XI", "Away XI")
    ogs = [e for e in r.events if e.metadata.get("own_goal")]
    assert len(ogs) == 1
    assert ogs[0].team == Team.HOME
    assert ogs[0].player == "M. Ownnet"
    assert ogs[0].metadata["conceded_by"] == "M. Ownnet"


def test_measured_position_and_xg_survive():
    r = StatsBombAdapter().to_events(_events(), "Home XI", "Away XI")
    goal = next(e for e in r.events if e.outcome == "goal")
    assert goal.position.x == 110.5 and goal.position.y == 35.0
    assert "position_estimated" not in goal.metadata
    assert goal.metadata["xg_provider"] == 0.084
    assert goal.metadata["body_part"] == "left_foot"
    assert goal.metadata["assist"] == "A. Creator"
    assert goal.metadata["provider_event_id"] == "bbb1"


def test_provenance_and_unmapped_counting():
    r = StatsBombAdapter().to_events(_events(), "Home XI", "Away XI")
    p = r.provenance
    assert p["provider"] == "statsbomb-open-data"
    assert p["license"] == "CC-BY-4.0"
    assert p["unmapped_types"] == {"Goal Keeper": 1, "Own Goal Against": 1}
    assert p["reported_xg"] == {"home": 0.0, "away": 0.084}


def test_timestamp_parsed_not_field_minute():
    r = StatsBombAdapter().to_events(_events(), "Home XI", "Away XI")
    og = next(e for e in r.events if e.metadata.get("own_goal"))
    assert (og.minute, og.second) == (17, 56)
    assert og.id == f"sb_sb_match_{0:04d}"


def test_sub_and_card_details():
    r = StatsBombAdapter().to_events(_events(), "Home XI", "Away XI")
    sub = next(e for e in r.events if e.type == EventType.SUBSTITUTION)
    assert sub.metadata["player_in"] == "F. On" and sub.player == "T. Off"
    foul = next(e for e in r.events if e.type == EventType.FOUL)
    assert foul.metadata["card"] == "yellow" and foul.outcome == "yellow"


def test_ad_narrates_real_direction():
    r = StatsBombAdapter().to_events(_events(), "Home XI", "Away XI")
    goal = next(e for e in r.events if e.outcome == "goal")
    line = describe_event(goal, "Home XI", "Away XI")
    # y=35 is central — real data earns real channel wording
    assert "central" in line or "in the area" not in line


def test_gate_runs_on_statsbomb_ledger():
    r = StatsBombAdapter().to_events(_events(), "Home XI", "Away XI")
    gate = TrustGate(r.events)
    assert (
        gate.verify_line("Home XI lead 1-0 after the early mix-up!", minute=20)["status"]
        != "rejected"
    )
    assert gate.verify_line("It is 4-4 in a thriller!", minute=60)["status"] == "rejected"


def test_missing_location_flags_estimated():
    events = _events() + [
        {
            "id": "zzz1",
            "index": 200,
            "period": 2,
            "timestamp": "00:80:00.0",
            "minute": 80,
            "second": 0,
            "type": {"id": 30, "name": "Pass"},
            "team": {"id": 1, "name": "Home XI"},
            "player": {"id": 1, "name": "N. Olocation"},
        }
    ]
    r = StatsBombAdapter().to_events(events, "Home XI", "Away XI")
    noloc = next(e for e in r.events if e.player == "N. Olocation")
    assert noloc.metadata["position_estimated"] is True
    assert r.provenance["positions_estimated"] is True
