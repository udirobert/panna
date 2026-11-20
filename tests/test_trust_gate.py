"""TrustGate — the packaged verification layer, standalone from broadcast."""

from __future__ import annotations

import json

from src.agents.verifier import _Facts  # noqa: SLF001
from src.events.generator import MatchConfig, SyntheticMatchGenerator
from src.trust import JsonlLedger, TrustGate, translation_intact


def _fixture():
    events = SyntheticMatchGenerator(MatchConfig(match_id="m_trust", seed=7)).generate()
    return events, _Facts(events)


def test_gate_verifies_truthful_and_rejects_fabricated(tmp_path):
    events, facts = _fixture()
    gate = TrustGate(events, audit=JsonlLedger(tmp_path / "a.jsonl"))

    goal = next(e for e in events if e.type.value == "goal")
    h, a = facts.score_at(goal.minute)
    assert gate.verify_line(f"GOAL! It is {h}-{a} now.", minute=goal.minute)["status"] == "verified"
    assert (
        gate.verify_line("A finish worthy of the Premier League!", minute=30)["status"]
        == "rejected"
    )
    assert gate.verify_claim("Home dominated with 9.99 xG", evidence=[])["status"] == "rejected"

    # every verdict landed in the durable ledger
    rows = (tmp_path / "a.jsonl").read_text().splitlines()
    assert len(rows) == 3
    assert all(json.loads(r)["type"] == "verdict" for r in rows)


def test_gate_works_without_audit():
    events, _ = _fixture()
    gate = TrustGate(events)  # no ledger — must not raise
    verdict = gate.verify_line("The pattern is set early.", minute=5)
    assert verdict["status"] in ("verified", "repaired", "rejected")


def test_translation_intact_reexport():
    assert translation_intact("4-2 final", "4-2 final", "es") == []
    assert translation_intact("4-2 final", "final five-two", "es") != []
