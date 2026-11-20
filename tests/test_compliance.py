"""Article 50 readiness — the compliance artifact is real, not a slide."""

from __future__ import annotations

import json

from src.compliance import run_readiness, write_manifest, write_report


def test_readiness_manifest_covers_every_line(tmp_path, monkeypatch):
    monkeypatch.setattr("src.compliance.REPORTS_DIR", tmp_path)
    report = run_readiness(seed=137, match_id="m_art50_test")

    s = report["summary"]
    assert s["gated_lines"] > 0
    assert s["aired"] + s["suppressed"] == len(
        [line for line in report["lines"] if line["air_status"] in ("aired", "suppressed")]
    )
    # the planted attack was killed via the human-review path
    assert s["human_decisions"] == 2
    assert "rejected" in s["verdicts"]

    # every line carries a verdict + air status (the machine-readable mark)
    for line in report["lines"]:
        assert line["verdict"] in ("verified", "repaired", "rejected")
        assert isinstance(line["checks"], list)

    # the audit ledger actually landed on disk
    ledger = tmp_path / "audit-m_art50_test.jsonl"
    types = {json.loads(r)["type"] for r in ledger.read_text().splitlines()}
    assert {"session_start", "verdict", "aired", "suppressed", "decision"} <= types


def test_write_report_and_manifest(tmp_path):
    report = run_readiness(seed=137, match_id="m_art50_files")
    md = write_report(report, tmp_path / "r.md")
    manifest = write_manifest(report, tmp_path / "m.json")
    text = md.read_text()
    assert "Article 50" in text and "human editorial review" in text.lower()
    data = json.loads(manifest.read_text())
    assert data["art50"]["human_editorial_review"]
