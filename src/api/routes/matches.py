from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.events.generator import MatchConfig, SyntheticMatchGenerator

router = APIRouter()

_MATCHES: dict[str, list] = {}


@router.post("/generate")
def generate(match_id: str = "match_001", seed: int = 42) -> dict:
    cfg = MatchConfig(match_id=match_id, seed=seed)
    gen = SyntheticMatchGenerator(cfg)
    events = gen.generate()
    _MATCHES[match_id] = events
    return {"match_id": match_id, "event_count": len(events)}


@router.get("/{match_id}")
def get_match(match_id: str) -> dict:
    if match_id not in _MATCHES:
        raise HTTPException(404, "match not found; POST /matches/generate first")
    evs = _MATCHES[match_id]
    return {"match_id": match_id, "event_count": len(evs)}
