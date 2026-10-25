from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.agents.director import DirectorAgent
from src.api.routes.matches import _MATCHES

router = APIRouter()
_director = DirectorAgent()


@router.get("/{match_id}")
def get_recap(match_id: str) -> dict:
    if match_id not in _MATCHES:
        raise HTTPException(404, "match not found")
    events = _MATCHES[match_id]
    result = _director.run({"events": events})
    from src.agents.recap import RecapAgent

    recap_text = RecapAgent().run(
        {
            "insights": result["insights"],
            "key_moments": result["key_moments"],
        }
    )
    return {"match_id": match_id, "recap": recap_text}
