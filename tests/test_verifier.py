"""Verifier gate tests: honest lines pass; every planted lie is caught."""

import pytest

from src.agents.director import DirectorAgent
from src.agents.verifier import VerifierAgent, _Facts  # noqa: SLF001
from src.events.generator import MatchConfig, SyntheticMatchGenerator
from src.events.schema import CommentaryEntry, Insight
from src.redteam import run_redteam


@pytest.fixture(scope="module")
def events():
    return SyntheticMatchGenerator(MatchConfig(match_id="match_v", seed=7)).generate()


@pytest.fixture(scope="module")
def result(events):
    return DirectorAgent().run({"events": events})


def test_verifier_attached_to_every_broadcast_item(result):
    verdicts = result["verdicts"]
    assert result["verification"]["checked"] == len(verdicts) > 0
    for ins in result["insights"]:
        assert ins.verification is not None
    for c in result["commentary"]:
        assert c.verification is not None


def test_honest_lines_mostly_pass(result):
    """The gate must not be a red pen on everything — low false-positive tax."""
    summary = result["verification"]
    assert summary["rejected"] <= max(1, summary["checked"] // 4)


def test_fabricated_score_rejected(events):
    facts = _Facts(events)
    h, a = facts.score_at(80)
    entry = CommentaryEntry(id="t1", minute=80, second=0, text=f"And that makes it {h + 2}-{a}!")
    v = VerifierAgent().verify_commentary(entry, events)
    assert v.status == "rejected"
    assert any(c["kind"] == "score" and not c["ok"] for c in v.checks)


def test_invented_stat_rejected(events):
    entry = CommentaryEntry(id="t2", minute=30, second=0, text="A 37.84 km/h sprint won the ball!")
    v = VerifierAgent().verify_commentary(entry, events)
    assert v.status == "rejected"


def test_wrong_minute_goal_rejected(events):
    facts = _Facts(events)
    free = next(m for m in range(5, 89) if all(abs(m - g) > 1 for g in facts.goal_minutes))
    entry = CommentaryEntry(id="t3", minute=free, second=0, text=f"GOAL at {free}' — unstoppable!")
    v = VerifierAgent().verify_commentary(entry, events)
    assert v.status == "rejected"
    assert any(c["kind"] == "minute" and not c["ok"] for c in v.checks)


def test_wrong_xg_value_repaired(events):
    """A wrong xG total is fixable: repaired, not killed — and the aired
    number is the true one."""
    facts = _Facts(events)
    bad = Insight(
        id="t4",
        type="xg_total",
        claim=f"Home xG {facts.home_xg + 3.0:.2f} vs Away xG {facts.away_xg:.2f}",
        value=facts.home_xg + 3.0,
        confidence=0.9,
        evidence=[],
    )
    v = VerifierAgent().verify_insight(bad, events, facts)
    assert v.status == "repaired"
    assert v.repair_of == bad.claim


def test_redteam_catches_planted_lines():
    report = run_redteam(seed=42)
    assert report["catch_rate"] >= 5 / 6  # allow one marginal miss at most
    missed = [a for a in report["attacks"] if not a["caught"]]
    assert not missed or report["catch_rate"] >= 0.8
    # and the honest feed isn't shredded by the gate
    assert report["honest_rejection_rate"] <= 0.34


def test_verifier_rejects_banned_language():
    from src.agents.verifier import VerifierAgent, _Facts
    from src.events.generator import MatchConfig, SyntheticMatchGenerator

    events = SyntheticMatchGenerator(MatchConfig(match_id="m_lang", seed=5)).generate()
    facts = _Facts(events)
    v = VerifierAgent()
    checks = v.check_text("A guaranteed win — great odds on the Premier League leaders!", facts)
    lang = [c for c in checks if c["kind"] == "language"]
    assert lang and not lang[0]["ok"]
    assert set(lang[0]["actual"]) >= {"guaranteed", "odds", "premier league"}


def test_verifier_accepts_clean_language():
    from src.agents.verifier import VerifierAgent, _Facts
    from src.events.generator import MatchConfig, SyntheticMatchGenerator

    events = SyntheticMatchGenerator(MatchConfig(match_id="m_clean", seed=5)).generate()
    facts = _Facts(events)
    v = VerifierAgent()
    checks = v.check_text("What a strike!", facts)
    assert [c for c in checks if c["kind"] == "language"][0]["ok"]
