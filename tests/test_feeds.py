"""Tests for the feed layer — audience transforms + localization.

Every check exercises the per-viewer render pipeline (`src/feed.py`), which
applies audience and language AFTER the verifier gate on canonical output.
"""

import httpx
import pytest

from src import feed
from src.events.schema import Event, EventType, Position, Team
from src.foundry import translate as translate_mod
from src.foundry.translate import TranslatorClient


@pytest.fixture(autouse=True)
def _fresh_translator(monkeypatch):
    """Each test gets a clean singleton so auth/env never leaks between cases."""
    monkeypatch.setattr(translate_mod, "_client", None)


# ---- kids lexicon ----------------------------------------------------------


def test_kids_simplifies_jargon():
    payload = {"id": "c1", "minute": 30, "text": "The PPDA sits at 8.2, the xG at 0.4"}
    shaped = feed.audience_payload("commentary", payload, "kids")
    assert "pressing intensity" in shaped["text"] or "chasing the ball" in shaped["text"]
    assert "chance quality" in shaped["text"]
    assert "xG" not in shaped["text"]
    assert "8.2" in shaped["text"] and "0.4" in shaped["text"]  # numbers survive
    assert shaped["audience"] == "kids"


def test_kids_leaves_other_frames_alone():
    payload = {"id": "g1", "minute": 30}
    assert feed.audience_payload("goal", payload, "kids") == payload


def test_fan_and_analyst_passthrough():
    payload = {"id": "c1", "text": "hello"}
    assert feed.audience_payload("commentary", payload, "fan") == payload
    assert feed.audience_payload("commentary", payload, "analyst") == payload


# ---- audio description audience --------------------------------------------


def test_ad_suppresses_analytics_frames():
    assert feed.audience_payload("insight", {"claim": "x"}, "ad") is None
    assert feed.audience_payload("detection", {"minute": 3}, "ad") is None


def test_ad_render_appends_described_lines():
    events = [
        Event(
            id="evt_0001",
            match_id="m",
            minute=10,
            second=5,
            type=EventType.PASS,
            player="P3",
            team=Team.HOME,
            position=Position(x=60, y=40),
        ),
        Event(
            id="evt_0002",
            match_id="m",
            minute=11,
            second=7,
            type=EventType.GOAL,
            player="P9",
            team=Team.AWAY,
            position=Position(x=110, y=40),
            metadata={"body_part": "right_foot"},
        ),
    ]
    by_id = {e.id: e for e in events}
    batch = {"batch": [{"id": "evt_0001"}, {"id": "evt_0002"}]}
    frames = feed.render_frame(
        "events",
        batch,
        audience="ad",
        lang="en",
        cache={},
        events_by_id=by_id,
    )
    kinds = [k for k, _ in frames]
    assert "events" in kinds  # raw feed preserved for the pitch viz
    commentary = [p for k, p in frames if k == "commentary"]
    assert len(commentary) == 1  # the pass stays silent, the goal speaks
    assert "Goal for Away" in commentary[0]["text"]


# ---- translator client -----------------------------------------------------


def _mock_transport():
    def handler(request: httpx.Request) -> httpx.Response:
        import json as _json

        texts = [item["Text"] for item in _json.loads(request.content)]
        return httpx.Response(
            200,
            json=[{"translations": [{"text": f"ES:{t}", "to": "es"}]} for t in texts],
        )

    return httpx.MockTransport(handler)


def test_translator_unavailable_by_default(monkeypatch):
    for k in ("TRANSLATOR_KEY", "TRANSLATOR_REGION", "TRANSLATOR_AUTH"):
        monkeypatch.delenv(k, raising=False)
    c = TranslatorClient()
    assert not c.available
    assert c.auth_mode == "none"
    assert c.translate(["hello"], "es") is None


def test_translator_api_key_round_trip(monkeypatch):
    monkeypatch.setenv("TRANSLATOR_KEY", "k")
    monkeypatch.setenv("TRANSLATOR_REGION", "westeurope")
    c = TranslatorClient(transport=_mock_transport())
    out = c.translate(["Goal for Home", "What a save"], "es")
    assert out == ["ES:Goal for Home", "ES:What a save"]
    assert c.chars_sent == len("Goal for Home") + len("What a save")


def test_translator_failure_returns_none(monkeypatch):
    monkeypatch.setenv("TRANSLATOR_KEY", "k")
    c = TranslatorClient(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    assert c.translate(["x"], "es") is None


def test_translate_map_caches_and_labels(monkeypatch):
    monkeypatch.setenv("TRANSLATOR_KEY", "k")
    monkeypatch.setattr(translate_mod, "_client", TranslatorClient(transport=_mock_transport()))
    cache = {}
    first = feed.translate_map(["hello"], "es", cache)
    assert first == {"hello": "ES:hello"}
    again = feed.translate_map(["hello"], "es", cache)  # served from cache
    assert again == {"hello": "ES:hello"}


def test_localized_marks_provenance(monkeypatch):
    monkeypatch.delenv("TRANSLATOR_KEY", raising=False)
    monkeypatch.delenv("TRANSLATOR_AUTH", raising=False)
    monkeypatch.setattr(translate_mod, "_client", TranslatorClient())
    out = feed.localized({"text": "hello"}, "text", "es", {})
    assert out["text"] == "hello"
    assert out["translation"] == "original"  # honestly labelled, not silent


def test_localized_english_is_noop():
    out = feed.localized({"text": "hello"}, "text", "en", {})
    assert out["lang"] == "en"
    assert "translation" not in out


def test_render_frame_localizes_commentary(monkeypatch):
    monkeypatch.setenv("TRANSLATOR_KEY", "k")
    monkeypatch.setattr(translate_mod, "_client", TranslatorClient(transport=_mock_transport()))
    frames = feed.render_frame(
        "commentary", {"id": "c1", "text": "Goal for Home"}, audience="fan", lang="es", cache={}
    )
    assert frames[0][1]["text"] == "ES:Goal for Home"
    assert frames[0][1]["translation"] == "translator"


# ---- routes -----------------------------------------------------------------


def test_commentary_route_accepts_feed_params():
    from fastapi.testclient import TestClient

    from src.api.main import app

    c = TestClient(app)
    c.post("/matches/generate?match_id=feed_t1&seed=77")
    r = c.get("/commentary/feed_t1?lang=es&audience=fan")
    assert r.status_code == 200
    body = r.json()
    assert body["lang"] == "es"
    assert body["audience"] == "fan"
    # translator unconfigured → every line honest about serving the original
    assert all(p.get("translation") == "original" for p in body["commentary"])


def test_commentary_route_rejects_bad_feed_params():
    from fastapi.testclient import TestClient

    from src.api.main import app

    c = TestClient(app)
    c.post("/matches/generate?match_id=feed_t2&seed=77")
    assert c.get("/commentary/feed_t2?lang=xx").status_code == 400
    assert c.get("/commentary/feed_t2?audience=vip").status_code == 400


def test_insights_route_localizes_claims():
    from fastapi.testclient import TestClient

    from src.api.main import app

    c = TestClient(app)
    c.post("/matches/generate?match_id=feed_t3&seed=77")
    r = c.get("/insights/feed_t3?lang=fr")
    assert r.status_code == 200
    assert all(
        p.get("translation") == "original" or p.get("lang") == "fr" for p in r.json()["insights"]
    )


# ---- translation integrity ---------------------------------------------------


def test_translation_intact_passes_clean_translation():
    source = "P7 scores! It's 2-1 in the 74th minute."
    translated = "¡P7 marca! Es 2-1 en el minuto 74."
    assert feed.translation_intact(source, translated, "es") == []


def test_translation_intact_catches_mangled_number():
    problems = feed.translation_intact("Home lead 2-1", "Casa lidera 3-1", "es")
    assert any("numbers changed" in p for p in problems)


def test_translation_intact_catches_lost_player():
    problems = feed.translation_intact("P7 scores", "El delantero marca", "es")
    assert any("names lost" in p for p in problems)


def test_translation_intact_accepts_arabic_indic_digits():
    # ٢-١ in Arabic-Indic digits still counts as 2-1
    assert feed.translation_intact("Home lead 2-1", "تقدم ٢-١", "es") == []


def test_localized_falls_back_when_translation_mangles_numbers(monkeypatch):
    def mangler(texts, to):
        return [t.replace("2", "3") for t in texts]

    monkeypatch.setattr(
        translate_mod,
        "_client",
        type("T", (), {"available": True, "translate": staticmethod(mangler)})(),
    )
    out = feed.localized({"text": "Home lead 2-1"}, "text", "es", {})
    assert out["text"] == "Home lead 2-1"
    assert out["translation"] == "original"
    assert "numbers changed" in out["translation_problem"]
