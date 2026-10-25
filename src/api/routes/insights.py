from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.agents.analyst import AnalystAgent
from src.agents.scout import ScoutAgent
from src.api.routes.matches import _MATCHES

router = APIRouter()
_scout = ScoutAgent()
_analyst = AnalystAgent()


@router.get("/{match_id}")
def get_insights(match_id: str) -> dict:
    if match_id not in _MATCHES:
        raise HTTPException(404, "match not found")
    events = _MATCHES[match_id]
    ctx = {"events": events}
    key_moments = _scout.run(ctx)
    insights = _analyst.run(ctx)
    return {
        "match_id": match_id,
        "key_moments": [km.model_dump() for km in key_moments],
        "insights": [i.model_dump() for i in insights],
    }
