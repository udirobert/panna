from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.routes.matches import _MATCHES
from src.events.frames import event_frame

router = APIRouter()


@router.get("/{match_id}")
def list_events(match_id: str, limit: int = 100, offset: int = 0) -> dict:
    """Event ledger in the canonical flat frame (same shape the SSE stream
    and the MCP server emit — one wire format, no client-side normalization)."""
    if match_id not in _MATCHES:
        raise HTTPException(404, "match not found")
    evs = _MATCHES[match_id]
    chunk = evs[offset : offset + limit]
    return {"match_id": match_id, "total": len(evs), "events": [event_frame(e) for e in chunk]}
