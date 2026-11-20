"""Speech client + audit ledger — honest staged behavior, durable records."""

from __future__ import annotations

import json

import httpx

from src.audit import JsonlLedger, NullLedger, load_audit_ledger
from src.foundry.speech import SpeechClient


class _Mp3Transport(httpx.BaseTransport):
    """Captures the SSML and returns canned MP3 bytes."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if "bad" in request.read().decode():
            return httpx.Response(500, text="upstream")
        return httpx.Response(200, content=b"ID3FAKEMP3")


def test_speech_unconfigured_is_honest(monkeypatch):
    for var in ("SPEECH_KEY", "SPEECH_REGION", "SPEECH_AUTH", "SPEECH_ENDPOINT"):
        monkeypatch.delenv(var, raising=False)
    c = SpeechClient()
    assert not c.available
    assert c.auth_mode == "none"
    assert c.synthesize("hello") is None


def test_speech_synthesize_sends_ssml(monkeypatch):
    monkeypatch.setenv("SPEECH_KEY", "k")
    monkeypatch.setenv("SPEECH_REGION", "westeurope")
    t = _Mp3Transport()
    c = SpeechClient(transport=t)
    assert c.available and c.auth_mode == "api-key"
    audio = c.synthesize("P7 scores with his left foot!")
    assert audio == b"ID3FAKEMP3"
    req = t.requests[0]
    assert "westeurope.tts.speech.microsoft.com" in str(req.url)
    body = req.read().decode()
    assert "<speak" in body and "P7 scores with his left foot!" in body
    assert req.headers["Ocp-Apim-Subscription-Key"] == "k"
    assert c.chars_sent == len("P7 scores with his left foot!")


def test_speech_escapes_ssml_and_fails_soft(monkeypatch):
    monkeypatch.setenv("SPEECH_KEY", "k")
    monkeypatch.setenv("SPEECH_REGION", "westeurope")
    t = _Mp3Transport()
    c = SpeechClient(transport=t)
    assert c.synthesize('a <b> & "quotes"') == b"ID3FAKEMP3"
    assert "&lt;b&gt;" in t.requests[0].read().decode()
    assert c.synthesize("this is bad text") is None  # upstream 500 → None


def test_speak_route_503s_honestly_when_unconfigured(monkeypatch):
    for var in ("SPEECH_KEY", "SPEECH_REGION", "SPEECH_AUTH", "SPEECH_ENDPOINT"):
        monkeypatch.delenv(var, raising=False)
    import src.foundry.speech as sp

    monkeypatch.setattr(sp, "_client", SpeechClient())
    from fastapi.testclient import TestClient

    from src.api.main import app

    resp = TestClient(app).post("/audio/speak", json={"text": "hello"})
    assert resp.status_code == 503
    assert resp.json()["detail"]["speech"] == "unconfigured"


def test_jsonl_ledger_roundtrip(tmp_path):
    led = JsonlLedger(tmp_path / "audit.jsonl")
    led.record({"type": "verdict", "id": "x", "status": "rejected"})
    led.record({"type": "decision", "id": "x", "decision": "kill"})
    rows = [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text().splitlines()]
    assert [r["type"] for r in rows] == ["verdict", "decision"]
    assert all("ts" in r for r in rows)


def test_load_audit_ledger_env(tmp_path):
    assert isinstance(load_audit_ledger({"PANNA_AUDIT": "off"}), NullLedger)
    led = load_audit_ledger({"PANNA_AUDIT_PATH": str(tmp_path / "a.jsonl")})
    assert isinstance(led, JsonlLedger)
    NullLedger().record({"type": "x"})  # no-op must not raise


def test_session_records_audit(tmp_path):
    """A live session writes session_start + verdict rows to the ledger."""
    from src.agents.director import DirectorAgent
    from src.api.session import MatchSession
    from src.events.generator import MatchConfig, SyntheticMatchGenerator

    events = SyntheticMatchGenerator(MatchConfig(match_id="m_audit", seed=7)).generate()
    result = DirectorAgent().run({"events": events})
    led = JsonlLedger(tmp_path / "audit.jsonl")
    MatchSession(
        match_id="m_audit",
        seed=7,
        home_team="Home FC",
        away_team="Away United",
        events=events,
        result=result,
        audit=led,
    )
    rows = [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text().splitlines()]
    types = [r["type"] for r in rows]
    assert "session_start" in types
    assert "verdict" in types
    assert all(r["id"] for r in rows if r["type"] == "verdict")
