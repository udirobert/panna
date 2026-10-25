"""Agentic narrative endpoints: Foundry-backed commentary + governance tracing."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.agents.director import DirectorAgent
from src.api.routes.matches import _MATCHES
from src.foundry import narrative
from src.foundry.tracing import summary_for, to_dicts

router = APIRouter()
_director = DirectorAgent()


@router.get("/narrate/{match_id}")
def narrate(match_id: str) -> dict:
    """Booth pass: Foundry LLM broadcast commentary (deterministic fallback).

    One structured call turns the match's key moments + insights into timed
    lines. The response carries its provenance (source, model) so the UI can
    show whether the narrative is model-generated or template-fallback.
    """
    if match_id not in _MATCHES:
        raise HTTPException(404, "match not found")
    events = _MATCHES[match_id]
    result = _director.run({"events": events})
    out = narrative.booth_commentary(
        match_id,
        {"key_moments": result["key_moments"], "insights": result["insights"]},
    )
    return {
        "match_id": match_id,
        "commentary": out["result"],
        "source": out["source"],
        "model": out["model"],
        "status": out["status"],
    }


@router.get("/tracing/{match_id}")
def tracing(match_id: str, detail: bool = False) -> dict:
    """Governance: traced spans for every agent step in this match."""
    data = summary_for(match_id)
    if detail:
        data["spans"] = to_dicts(match_id)
    return data
