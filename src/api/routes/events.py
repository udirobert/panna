from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.routes.matches import _MATCHES

router = APIRouter()


@router.get("/{match_id}")
def list_events(match_id: str, limit: int = 100, offset: int = 0) -> dict:
    if match_id not in _MATCHES:
        raise HTTPException(404, "match not found")
    evs = _MATCHES[match_id]
    chunk = evs[offset : offset + limit]
    return {"match_id": match_id, "total": len(evs), "events": [e.model_dump() for e in chunk]}
