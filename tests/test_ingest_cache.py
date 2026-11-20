"""Ingest disk cache — immutable data cached forever, fail-soft by contract."""

from __future__ import annotations

import httpx
import pytest

import src.ingest.cache as cache
from src.ingest import StatsBombAdapter


@pytest.fixture(autouse=True)
def _tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "DIR", tmp_path)
    monkeypatch.setattr(cache, "_DISABLED", False)
    return tmp_path


def test_write_read_roundtrip():
    cache.write("statsbomb-events", 8658, [{"id": "x"}])
    assert cache.read("statsbomb-events", 8658) == [{"id": "x"}]


def test_missing_key_is_miss():
    assert cache.read("statsbomb-events", "nonexistent") is None


def test_ttl_expiry(tmp_path):
    cache.TTL["test-ns"] = 0.0
    cache.write("test-ns", "k", {"v": 1})
    assert cache.read("test-ns", "k") is None  # already stale


def test_corrupt_entry_is_miss(tmp_path):
    p = cache.DIR / "statsbomb-events" / "bad.json"
    p.parent.mkdir(parents=True)
    p.write_text("not json{{{")
    assert cache.read("statsbomb-events", "bad") is None


def test_disabled_skips_reads_and_writes(monkeypatch):
    monkeypatch.setattr(cache, "_DISABLED", True)
    cache.write("statsbomb-events", 1, [{"a": 1}])
    assert cache.read("statsbomb-events", 1) is None


def test_key_sanitization():
    p = cache._path("ns", "../etc/../../danger")
    assert p.parent.name == "ns" and ".." not in p.name


def test_fetch_second_call_hits_cache(monkeypatch):
    """One live fetch, then all subsequent reads come from disk."""
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if "matches" in req.url.path:
            return httpx.Response(
                200,
                json=[
                    {
                        "match_id": 1,
                        "home_team": {"home_team_name": "H"},
                        "away_team": {"away_team_name": "A"},
                    }
                ],
            )
        return httpx.Response(200, json=[])

    adapter = StatsBombAdapter(transport=httpx.MockTransport(handler))
    r1 = adapter.fetch(43, 3, 1)
    assert r1 is not None and calls["n"] == 2
    assert r1.provenance["fetch_source"] == {"matches": "live", "events": "live"}

    adapter2 = StatsBombAdapter(transport=httpx.MockTransport(handler))
    r2 = adapter2.fetch(43, 3, 1)
    assert r2 is not None and calls["n"] == 2  # zero new HTTP calls
    assert r2.provenance["fetch_source"] == {"matches": "cache", "events": "cache"}


def test_refresh_bypasses_cache(monkeypatch):
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if "matches" in req.url.path:
            return httpx.Response(
                200,
                json=[
                    {
                        "match_id": 1,
                        "home_team": {"home_team_name": "H"},
                        "away_team": {"away_team_name": "A"},
                    }
                ],
            )
        return httpx.Response(200, json=[])

    adapter = StatsBombAdapter(transport=httpx.MockTransport(handler))
    adapter.fetch(43, 3, 1)
    assert calls["n"] == 2
    adapter.fetch(43, 3, 1, refresh=True)
    assert calls["n"] == 4  # refetched both
