"""Tests for the deterministic audio-description feed."""

from src.events.audio import audio_line, describe_event
from src.events.schema import Event, EventType, Position, Team


def _ev(type_, **kw) -> Event:
    defaults = dict(
        id="evt_0001",
        match_id="m",
        minute=23,
        second=41,
        type=type_,
        player="P7",
        team=Team.HOME,
        position=Position(x=105.0, y=22.0),
    )
    defaults.update(kw)
    return Event(**defaults)


def test_goal_described_with_body_part_and_channel():
    e = _ev(EventType.GOAL, metadata={"body_part": "head", "xg": 0.4})
    line = describe_event(e, "Rovers", "City")
    assert line is not None
    assert "Goal for Rovers" in line
    assert "P7" in line
    assert "head" in line
    assert "left" in line  # y=22 < 26.7


def test_shot_on_target_mentions_keeper():
    e = _ev(EventType.SHOT, outcome="on_target", metadata={"body_part": "left_foot"})
    line = describe_event(e, "Rovers", "City")
    assert "goalkeeper" in line
    assert "left foot" in line


def test_shot_off_target():
    e = _ev(EventType.SHOT, outcome="off_target")
    assert "away from goal" in describe_event(e, "Rovers", "City")


def test_tackle_outcomes():
    won = _ev(EventType.TACKLE, outcome="success", position=Position(x=50, y=40))
    lost = _ev(EventType.TACKLE, outcome="unsuccessful", position=Position(x=50, y=40))
    assert "wins the ball cleanly" in describe_event(won, "Rovers", "City")
    assert "skips past" in describe_event(lost, "Rovers", "City")


def test_card_is_named():
    e = _ev(EventType.FOUL, outcome="red", metadata={"card": "red"})
    line = describe_event(e, "Rovers", "City")
    assert "red card" in line


def test_plain_foul_no_card():
    e = _ev(EventType.FOUL, outcome="none", metadata={"card": "none"})
    assert "free kick" in describe_event(e, "Rovers", "City")


def test_set_piece_type():
    e = _ev(EventType.SET_PIECE, metadata={"set_piece_type": "corner"})
    assert "corner" in describe_event(e, "Rovers", "City")


def test_substitution_names_player_in():
    e = _ev(EventType.SUBSTITUTION, player="P4", metadata={"player_in": "P9"})
    line = describe_event(e, "Rovers", "City")
    assert "P9 comes on in place of P4" in line


def test_formation_described():
    e = _ev(EventType.FORMATION_CHANGE, metadata={"formation": "4-3-3", "side": "home"})
    assert "4-3-3" in describe_event(e, "Rovers", "City")


def test_routine_events_silent():
    for t in (EventType.PASS, EventType.CARRY, EventType.PRESSURE, EventType.INTERCEPTION):
        assert describe_event(_ev(t), "Rovers", "City") is None
        assert audio_line(_ev(t), "Rovers", "City") is None


def test_audio_line_is_commentary_shaped():
    line = audio_line(_ev(EventType.GOAL, metadata={"body_part": "head"}), "Rovers", "City")
    assert line["id"] == "ad:evt_0001"
    assert line["minute"] == 23
    assert line["tone"] == "audio-description"
    assert line["audience"] == "ad"
    assert line["verification"] is None  # code-generated — verifiable by construction
