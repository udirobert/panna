from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.events.generator import MatchConfig, SyntheticMatchGenerator

router = APIRouter()

_MATCHES: dict[str, list] = {}
_CONFIGS: dict[str, MatchConfig] = {}


@router.post("/generate")
def generate(match_id: str = "match_001", seed: int = 42) -> dict:
    cfg = MatchConfig(match_id=match_id, seed=seed)
    gen = SyntheticMatchGenerator(cfg)
    events = gen.generate()
    _MATCHES[match_id] = events
    _CONFIGS[match_id] = cfg
    return {"match_id": match_id, "event_count": len(events)}


@router.get("/resolve/{match_id}")
def resolve(match_id: str) -> dict:
    """Make a match live and return its identity.

    This is the viral primitive: matches are fully deterministic per seed, so
    a URL like ``/share?seed=137`` boots *any* visitor into the identical
    match. ``resolve`` guarantees the match exists (regenerating from its seed
    if the process restarted) and reports the seed so the frontend can echo it.
    """
    cfg = _CONFIGS.get(match_id)
    if cfg is None:
        # derive seed from a "match_<seed>" id, else default
        seed = 42
        if match_id.startswith("match_") and match_id[6:].isdigit():
            seed = int(match_id[6:])
        cfg = MatchConfig(match_id=match_id, seed=seed)
        gen = SyntheticMatchGenerator(cfg)
        _MATCHES[match_id] = gen.generate()
        _CONFIGS[match_id] = cfg
    elif match_id not in _MATCHES:
        gen = SyntheticMatchGenerator(cfg)
        _MATCHES[match_id] = gen.generate()
    return {
        "match_id": match_id,
        "seed": cfg.seed,
        "home_team": cfg.home_team,
        "away_team": cfg.away_team,
        "event_count": len(_MATCHES[match_id]),
    }


@router.get("/{match_id}")
def get_match(match_id: str) -> dict:
    if match_id not in _MATCHES:
        raise HTTPException(404, "match not found; POST /matches/generate first")
    evs = _MATCHES[match_id]
    return {"match_id": match_id, "event_count": len(evs)}
