from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.events.generator import MatchConfig, SyntheticMatchGenerator

router = APIRouter()

_MATCHES: dict[str, list] = {}
_CONFIGS: dict[str, MatchConfig] = {}
_PROVENANCE: dict[str, dict] = {}


def _prebuild_session(cfg: MatchConfig) -> None:
    """Run the agent pipeline now (on the thread pool, not the event loop)
    so the first stream connection opens instantly even when Foundry is live.
    A failed pre-build just defers the work to first connect (the stream
    endpoint builds on demand), so nothing here is fatal."""
    import logging
    from contextlib import suppress

    from src.api.session import get_or_create_session

    with suppress(Exception) as caught:
        get_or_create_session(
            cfg.match_id,
            _MATCHES[cfg.match_id],
            seed=cfg.seed,
            home_team=cfg.home_team,
            away_team=cfg.away_team,
        )
    if caught is not None:
        logging.getLogger(__name__).debug("pre-build failed for %s: %s", cfg.match_id, caught)


@router.post("/generate")
def generate(match_id: str = "match_001", seed: int = 42) -> dict:
    cfg = MatchConfig(match_id=match_id, seed=seed)
    gen = SyntheticMatchGenerator(cfg)
    events = gen.generate()
    _MATCHES[match_id] = events
    _CONFIGS[match_id] = cfg
    _prebuild_session(cfg)
    return {"match_id": match_id, "event_count": len(events)}


class IngestBody(BaseModel):
    provider: str = "statsbomb"
    match_id: str = ""
    competition_id: int = 43
    season_id: int = 3
    fixture_id: str = ""
    refresh: bool = False


@router.post("/ingest")
def ingest(body: IngestBody) -> dict:
    """Load a real provider match so the whole broadcast pipeline — stream,
    producer console, feeds — runs on licensed/open data. The match_id it
    returns (``sb_*``/``sm_*``) resolves like any generated match."""
    from src.ingest import SportmonksAdapter, StatsBombAdapter

    if body.provider == "statsbomb":
        if not body.match_id:
            raise HTTPException(400, "statsbomb needs match_id")
        result = StatsBombAdapter().fetch(
            body.competition_id, body.season_id, int(body.match_id), refresh=body.refresh
        )
        real_id = f"sb_{body.match_id}"
    else:
        if not body.fixture_id:
            raise HTTPException(400, "sportmonks needs fixture_id")
        result = SportmonksAdapter().fetch(body.fixture_id, refresh=body.refresh)
        real_id = f"sm_{body.fixture_id}"
    if result is None:
        raise HTTPException(502, "provider fetch failed — no token, no network, or unknown id")
    prov = result.provenance
    _MATCHES[real_id] = result.events
    _PROVENANCE[real_id] = prov
    _CONFIGS[real_id] = MatchConfig(
        match_id=real_id,
        seed=0,
        home_team=prov.get("home_team") or "Home",
        away_team=prov.get("away_team") or "Away",
    )
    _prebuild_session(_CONFIGS[real_id])
    return {
        "match_id": real_id,
        "event_count": len(result.events),
        "provenance": prov,
    }


@router.get("/resolve/{match_id}")
def resolve(match_id: str) -> dict:
    """Make a match live and return its identity.

    This is the viral primitive: matches are fully deterministic per seed, so
    a URL like ``/share?seed=137`` boots *any* visitor into the identical
    match. ``resolve`` guarantees the match exists (regenerating from its seed
    if the process restarted) and reports the seed so the frontend can echo it.
    Real-match ids (``sb_*``/``sm_*``) must be ingested first — silently
    generating a synthetic match under a real id would lie about the data.
    """
    if (match_id.startswith("sb_") or match_id.startswith("sm_")) and match_id not in _CONFIGS:
        raise HTTPException(404, "real match not ingested — POST /matches/ingest first")
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
    _prebuild_session(cfg)
    return {
        "match_id": match_id,
        "seed": cfg.seed,
        "home_team": cfg.home_team,
        "away_team": cfg.away_team,
        "event_count": len(_MATCHES[match_id]),
        "data_source": _PROVENANCE.get(match_id, "synthetic"),
    }


@router.get("/{match_id}")
def get_match(match_id: str) -> dict:
    if match_id not in _MATCHES:
        raise HTTPException(404, "match not found; POST /matches/generate first")
    evs = _MATCHES[match_id]
    return {"match_id": match_id, "event_count": len(evs)}
