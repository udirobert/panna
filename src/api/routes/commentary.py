from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.agents.director import DirectorAgent
from src.api.routes.matches import _MATCHES
from src.feed import AUDIENCES, render_frame
from src.foundry.translate import LANGUAGES

router = APIRouter()
_director = DirectorAgent()


@router.get("/{match_id}")
def get_commentary(match_id: str, lang: str = "en", audience: str = "fan") -> dict:
    if match_id not in _MATCHES:
        raise HTTPException(404, "match not found")
    if lang not in LANGUAGES:
        raise HTTPException(400, f"lang must be one of {LANGUAGES}")
    if audience not in AUDIENCES:
        raise HTTPException(400, f"audience must be one of {AUDIENCES}")
    events = _MATCHES[match_id]
    result = _director.run({"events": events})
    commentary = result.get("commentary", []) or []
    serialized = [c.model_dump() if hasattr(c, "model_dump") else c for c in commentary]

    # per-request feed rendering: audience transform, then localization on the
    # already-verified canonical text
    cache: dict[tuple[str, str], str] = {}
    rendered = []
    for c in serialized:
        for _, p in render_frame("commentary", c, audience=audience, lang=lang, cache=cache):
            rendered.append(p)
    return {
        "match_id": match_id,
        "lang": lang,
        "audience": audience,
        "commentary": rendered,
        "commentary_source": result.get("commentary_source", "template"),
        "feed": result.get("feed", []),
        "health": result.get("health", {}),
    }
