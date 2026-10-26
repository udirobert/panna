"""Canonical event frame — the one wire shape for a match event.

Every consumer (REST ledger, SSE stream, MCP tools, the share poster) reads
this same flat shape. It mirrors the StatsBomb-like ``Event`` model but is
presentation-ready: positions flattened, no nested ``position``/``end_location``.
REST previously returned the nested model and SSE the flat frame; that
divergence forced a client-side normalizer and is now gone.
"""

from __future__ import annotations

from src.events.schema import Event


def event_frame(e: Event) -> dict:
    """Flatten a StatsBomb-like Event into the canonical wire frame."""
    return {
        "id": e.id,
        "type": e.type.value,
        "team": e.team.value,
        "player": e.player,
        "minute": e.minute,
        "second": e.second,
        "x": e.position.x,
        "y": e.position.y,
        "end_x": e.end_location.x if e.end_location else None,
        "end_y": e.end_location.y if e.end_location else None,
        "outcome": e.outcome,
        "xg": e.metadata.get("xg"),
    }
