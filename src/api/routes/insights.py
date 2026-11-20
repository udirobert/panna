from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.agents.analyst import AnalystAgent
from src.agents.scout import ScoutAgent
from src.api.routes.matches import _MATCHES
from src.feed import localized
from src.foundry.translate import LANGUAGES

router = APIRouter()
_scout = ScoutAgent()
_analyst = AnalystAgent()


@router.get("/{match_id}")
def get_insights(match_id: str, lang: str = "en") -> dict:
    if match_id not in _MATCHES:
        raise HTTPException(404, "match not found")
    if lang not in LANGUAGES:
        raise HTTPException(400, f"lang must be one of {LANGUAGES}")
    events = _MATCHES[match_id]
    ctx = {"events": events}
    key_moments = _scout.run(ctx)
    insights = _analyst.run(ctx)
    cache: dict[tuple[str, str], str] = {}
    return {
        "match_id": match_id,
        "lang": lang,
        "key_moments": [km.model_dump() for km in key_moments],
        "insights": [localized(i.model_dump(), "claim", lang, cache) for i in insights],
    }
