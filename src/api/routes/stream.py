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
from src.api.session import get_or_create_session, get_session

router = APIRouter()

_VALID_ACTIONS = {"play", "pause", "seek", "speed", "fail", "recover"}
_VALID_AGENTS = {"scout", "analyst", "commentator"}


class PlaybackCmd(BaseModel):
    action: str = Field(..., description="one of play|pause|seek|speed|fail|recover")
    at: float | None = Field(None, description="seek target in match seconds (0-5400)")
    speed: float | None = Field(None, description="match-seconds per real second")
    agent: str | None = Field(None, description="specialist to fail/recover")


def _sse(kind: str, data: dict[str, Any]) -> str:
    return f"event: {kind}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


@router.get("/{match_id}")
async def stream(match_id: str, request: Request) -> StreamingResponse:
    if match_id not in _MATCHES:
        raise HTTPException(404, "match not found; POST /matches/generate first")
    cfg = _CONFIGS.get(match_id)
    session = get_or_create_session(
        match_id,
        _MATCHES[match_id],
        seed=cfg.seed if cfg else 42,
        home_team=cfg.home_team if cfg else "Home FC",
        away_team=cfg.away_team if cfg else "Away United",
    )

    async def gen() -> Any:
        # re-sync on epoch changes (seek/reset from the controls)
        last_epoch = session.epoch
        yield _sse("snapshot", session.snapshot())
        while True:
            # bounded disconnect probe: never let the check itself hang the loop
            try:
                with anyio.fail_after(0.2):
                    if await request.is_disconnected():
                        break
            except TimeoutError:
                pass
            if session.epoch != last_epoch:
                last_epoch = session.epoch
                yield _sse("snapshot", session.snapshot())
            for kind, payload in session.advance():
                yield _sse(kind, payload)
            await asyncio.sleep(0.4)

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

    return {
        "match_id": match_id,
        "clock": int(session.clock),
        "minute": int(session.clock // 60),
        "playing": session.playing,
        "speed": session.speed,
        "failed": sorted(session.failed),
        "score": session.score(),
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
    }
