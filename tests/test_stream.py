"""Tests for the SSE replay session + playback controls."""

import socket
import subprocess
import sys
import time
import urllib.request

import httpx
import pytest

from src.api.session import get_or_create_session
from src.events.generator import MatchConfig, SyntheticMatchGenerator


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def live_server():
    """Real uvicorn server — TestClient's portal deadlocks on infinite SSE."""
    port = _free_port()
    proc = subprocess.Popen(  # noqa: S603
        [sys.executable, "-m", "uvicorn", "src.api.main:app", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(f"{base}/health", timeout=1)  # noqa: S310
            break
        except Exception:  # noqa: BLE001
            time.sleep(0.1)
    yield base
    proc.terminate()
    proc.wait(timeout=5)


def test_session_timeline_and_momentum():
    events = SyntheticMatchGenerator(MatchConfig(seed=3)).generate()
    s = get_or_create_session("sess_test", events, seed=3)
    assert len(s.timeline) >= len(events)
    kinds = {k for _, k, _, _ in s.timeline}
    assert {"event", "detection", "insight", "commentary"} <= kinds
    # momentum series cover full match
    assert len(s.momentum_series["home_cum"]) == 91
    # seek forward then back recomputes reveal state
    s.seek(3000)
    assert s.clock == 3000
    snap = s.snapshot()
    assert len(snap["momentum"]["home_cum"]) == snap["minute"] + 1
    # snapshot carries the full event ledger up to the clock (board survives seeks)
    assert len(snap["events"]) > 0
    s.seek(0)
    assert s.snapshot()["insights"] == []
    # at clock 0 only the kickoff events (t=0) are on the board
    zero = s.snapshot()["events"]
    assert all(ev["minute"] == 0 and ev["second"] == 0 for ev in zero)


def test_session_failure_and_recovery_flush():
    events = SyntheticMatchGenerator(MatchConfig(seed=5)).generate()
    s = get_or_create_session("sess_fail", events, seed=5)
    s.fail("analyst")
    s.seek(0)
    s.play()
    s.clock = 5400.0  # jump to end while analyst is dark
    s._cursor = 0  # noqa: SLF001
    s._minute_cursor = 1  # noqa: SLF001
    frames = s.advance()
    frame_kinds = [k for k, _ in frames]
    assert "insight" not in frame_kinds  # buffered, not revealed
    assert s._pending  # noqa: SLF001
    s.recover("analyst")
    frames = s.advance()
    recovered = [p for k, p in frames if k == "insight" and p.get("recovered")]
    assert recovered, "buffered insights should flush with recovered=true"


def test_stream_endpoint_and_playback_controls(live_server):
    r = httpx.post(f"{live_server}/matches/generate?match_id=st1&seed=9", timeout=10)
    assert r.status_code == 200

    kinds_seen: set[str] = set()
    with httpx.stream("GET", f"{live_server}/stream/st1", timeout=10) as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            if line.startswith("event: "):
                kinds_seen.add(line[7:])
            if {"snapshot", "clock"} <= kinds_seen:
                break
    assert {"snapshot", "events", "momentum", "clock"} <= kinds_seen

    r = httpx.post(
        f"{live_server}/stream/playback/st1", json={"action": "seek", "at": 1800}, timeout=10
    )
    assert r.status_code == 200
    assert r.json()["clock"] == 1800
    r = httpx.post(
        f"{live_server}/stream/playback/st1", json={"action": "speed", "speed": 120}, timeout=10
    )
    assert r.json()["speed"] == 120.0
    r = httpx.post(
        f"{live_server}/stream/playback/st1",
        json={"action": "fail", "agent": "analyst"},
        timeout=10,
    )
    assert r.json()["failed"] == ["analyst"]
    r = httpx.post(
        f"{live_server}/stream/playback/st1",
        json={"action": "recover", "agent": "analyst"},
        timeout=10,
    )
    assert r.json()["failed"] == []
    r = httpx.post(f"{live_server}/stream/playback/st1", json={"action": "nope"}, timeout=10)
    assert r.status_code == 400

    # seek re-emits a snapshot frame on the live stream
    with httpx.stream("GET", f"{live_server}/stream/st1", timeout=10) as resp:
        sent_seek = False
        resynced = False
        for line in resp.iter_lines():
            if not sent_seek:
                sent_seek = True
                httpx.post(
                    f"{live_server}/stream/playback/st1",
                    json={"action": "seek", "at": 1800},
                    timeout=10,
                )
                continue
            if line.startswith("event: snapshot"):
                resynced = True
                break
        assert resynced, "seek should re-emit snapshot"


def test_rebuild_session_on_regenerate(live_server):
    httpx.post(f"{live_server}/matches/generate?match_id=st2&seed=11", timeout=10)
    with httpx.stream("GET", f"{live_server}/stream/st2", timeout=10) as resp:
        for line in resp.iter_lines():
            if line.startswith("data: ") and '"seed":11' in line:
                break
    httpx.post(f"{live_server}/matches/generate?match_id=st2&seed=12", timeout=10)
    with httpx.stream("GET", f"{live_server}/stream/st2", timeout=10) as resp:
        saw_new_seed = False
        for line in resp.iter_lines():
            if line.startswith("data: ") and '"seed":12' in line:
                saw_new_seed = True
                break
        assert saw_new_seed, "regeneration should rebuild the session with the new seed"
