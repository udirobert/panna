"""SSE replay stream + playback controls for "The Verdict" demo film.

- ``GET  /stream/{match_id}``           — live SSE feed (snapshot, then timed frames)
- ``POST /playback/{match_id}``         — play / pause / seek / speed / fail / recover
- ``GET  /playback/{match_id}``         — current clock + score + failed clusters
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import anyio
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from src.api.routes.matches import _CONFIGS, _MATCHES
from src.api.session import get_or_create_session, get_session, session_for
from src.feed import AUDIENCES, render_frame
from src.foundry.translate import LANGUAGES

router = APIRouter()

_VALID_ACTIONS = {"play", "pause", "seek", "speed", "fail", "recover", "seed_bad_claim"}
_VALID_AGENTS = {"scout", "analyst", "commentator"}


class PlaybackCmd(BaseModel):
    action: str = Field(..., description="one of play|pause|seek|speed|fail|recover|seed_bad_claim")
    at: float | None = Field(None, description="seek target in match seconds (0-5400)")
    speed: float | None = Field(None, description="match-seconds per real second")
    agent: str | None = Field(None, description="specialist to fail/recover")


def _sse(kind: str, data: dict[str, Any]) -> str:
    return f"event: {kind}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


@router.get("/{match_id}")
async def stream(
    match_id: str,
    request: Request,
    autoplay: bool = False,
    lang: str = "en",
    audience: str = "fan",
) -> StreamingResponse:
    if match_id not in _MATCHES:
        raise HTTPException(404, "match not found; POST /matches/generate first")
    if lang not in LANGUAGES:
        raise HTTPException(400, f"lang must be one of {LANGUAGES}")
    if audience not in AUDIENCES:
        raise HTTPException(400, f"audience must be one of {AUDIENCES}")
    cfg = _CONFIGS.get(match_id)
    session = session_for(match_id, _MATCHES[match_id])
    if session is None:
        # first viewer (or a regenerated match): run the agent pipeline on a
        # worker thread so a Foundry round-trip never blocks the event loop
        session = await asyncio.to_thread(
            get_or_create_session,
            match_id,
            _MATCHES[match_id],
            seed=cfg.seed if cfg else 42,
            home_team=cfg.home_team if cfg else "Home FC",
            away_team=cfg.away_team if cfg else "Away United",
        )
    if autoplay and session.autoplay_pending:
        # first connection for this session kicks off the match
        session.autoplay_pending = False
        session.play()
    session.add_viewer()

    def _render(kind: str, payload: dict) -> list[tuple[str, dict]]:
        return render_frame(
            kind,
            payload,
            audience=audience,
            lang=lang,
            cache=session.translation_cache,
            home_team=session.home_team,
            away_team=session.away_team,
            events_by_id=session.events_by_id,
        )

    def _rendered_snapshot() -> dict:
        snap = session.snapshot()
        for key, frame_kind in (
            ("commentary", "commentary"),
            ("insights", "insight"),
            ("key_moments", "detection"),
        ):
            rendered = []
            for payload in snap[key]:
                rendered.extend(p for _, p in _render(frame_kind, payload))
            snap[key] = rendered
        snap["lang"] = lang
        snap["audience"] = audience
        return snap

    async def gen() -> Any:
        # re-sync on epoch changes (seek/reset from the controls)
        last_epoch = session.epoch
        try:
            yield _sse("snapshot", _rendered_snapshot())
            while True:
                # bounded disconnect probe: never let the check hang the loop
                try:
                    with anyio.fail_after(0.2):
                        if await request.is_disconnected():
                            break
                except TimeoutError:
                    pass
                if session.epoch != last_epoch:
                    last_epoch = session.epoch
                    yield _sse("snapshot", _rendered_snapshot())
                for kind, payload in session.advance():
                    for k, p in _render(kind, payload):
                        yield _sse(k, p)
                await asyncio.sleep(0.4)
        finally:
            session.remove_viewer()  # last viewer out → matchday pauses

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/playback/{match_id}")
def playback(match_id: str, cmd: PlaybackCmd) -> dict:
    session = get_session(match_id)
    if session is None:
        raise HTTPException(404, "no active session; open /stream/{match_id} first")
    if cmd.action not in _VALID_ACTIONS:
        raise HTTPException(400, f"action must be one of {sorted(_VALID_ACTIONS)}")

    if cmd.action == "play":
        session.play()
    elif cmd.action == "pause":
        session.pause()
    elif cmd.action == "seek":
        if cmd.at is None:
            raise HTTPException(400, "seek requires 'at' (match seconds)")
        session.seek(cmd.at)
    elif cmd.action == "speed":
        if cmd.speed is None:
            raise HTTPException(400, "speed requires 'speed'")
        session.set_speed(cmd.speed)
    elif cmd.action in ("fail", "recover"):
        if cmd.agent not in _VALID_AGENTS:
            raise HTTPException(400, f"agent must be one of {sorted(_VALID_AGENTS)}")
        if cmd.action == "fail":
            session.fail(cmd.agent)
        else:
            session.recover(cmd.agent)
    elif cmd.action == "seed_bad_claim":
        # red-team demo: plant a fabricated line; the verifier must catch it
        return {"match_id": match_id, **session.seed_bad_claim()}

    return {
        "match_id": match_id,
        "clock": int(session.clock),
        "minute": int(session.clock // 60),
        "playing": session.playing,
        "speed": session.speed,
        "failed": sorted(session.failed),
        "score": session.score(),
        "viewers": session.viewers,
        "auto_paused": session.auto_paused,
    }


@router.get("/playback/{match_id}")
def playback_state(match_id: str) -> dict:
    session = get_session(match_id)
    if session is None:
        raise HTTPException(404, "no active session")
    return {
        "match_id": match_id,
        "clock": int(session.clock),
        "minute": int(session.clock // 60),
        "playing": session.playing,
        "speed": session.speed,
        "failed": sorted(session.failed),
        "score": session.score(),
        "viewers": session.viewers,
        "auto_paused": session.auto_paused,
    }
