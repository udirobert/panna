from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.agents.director import DirectorAgent
from src.api.routes.matches import _MATCHES

router = APIRouter()
_director = DirectorAgent()


@router.get("/{match_id}")
def get_commentary(match_id: str) -> dict:
    if match_id not in _MATCHES:
        raise HTTPException(404, "match not found")
    events = _MATCHES[match_id]
    result = _director.run({"events": events})
    commentary = result.get("commentary", []) or []
    serialized = [c.model_dump() if hasattr(c, "model_dump") else c for c in commentary]
    return {
        "match_id": match_id,
        "commentary": serialized,
        "feed": result.get("feed", []),
        "health": result.get("health", {}),
    }
