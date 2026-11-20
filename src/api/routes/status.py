"""``GET /status`` — the honest-systems endpoint.

Like MatchCast's ``/v1/status``: says plainly what is real (running in this
process) and what is staged (described, not wired) — plus the cost ledger the
judges asked for: tokens spent per match at list-price estimates, and whether
the matchday is burning anything while nobody watches.
"""

from __future__ import annotations

from fastapi import APIRouter

from src.api.session import _SESSIONS  # noqa: SLF001
from src.foundry.client import get_client
from src.foundry.tracing import spans_for, summary_for
from src.foundry.translate import AUDIENCES, LANGUAGES, get_translator

# list-price estimate per 1K tokens for the deployment class (honest label:
# this is an approximation, not metered billing)
_COST_PER_1K_IN = 0.00125
_COST_PER_1K_OUT = 0.01

router = APIRouter()


def _session_cost(match_id: str) -> dict:
    s = summary_for(match_id)
    tin = sum(sp.tokens_in or 0 for sp in spans_for(match_id))
    tout = sum(sp.tokens_out or 0 for sp in spans_for(match_id))
    return {
        **s,
        "tokens_in": tin,
        "tokens_out": tout,
        "est_cost_usd": round(tin / 1000 * _COST_PER_1K_IN + tout / 1000 * _COST_PER_1K_OUT, 4),
    }


@router.get("")
def status() -> dict:
    client = get_client()
    translator = get_translator()
    sessions = {}
    for mid, sess in _SESSIONS.items():
        sessions[mid] = {
            "viewers": sess.viewers,
            "playing": sess.playing,
            "auto_paused": sess.auto_paused,
            "verification": sess.result.get("verification", {}),
            "cost": _session_cost(mid),
        }
    return {
        "service": "panna",
        "real": {
            "event_engine": "deterministic generator, seeded (src/events)",
            "stats_engine": "xG / PPDA / momentum / influence / formation (src/models)",
            "verifier": "deterministic recount gate (src/agents/verifier.py)",
            "streaming": "in-process SSE replay clock",
            "foundry": {
                "available": client.available,
                "deployment": client.deployment,
                "auth_mode": client.auth_mode,
            },
            "mcp": "read-only football tools (src/mcp_server.py)",
            "feeds": {
                "languages": list(LANGUAGES),
                "audiences": list(AUDIENCES),
                "translator": {
                    "available": translator.available,
                    "auth_mode": translator.auth_mode,
                    "chars_sent": translator.chars_sent,
                },
                "audio_description": (
                    "deterministic, generated from event positions/outcomes "
                    "(src/events/audio.py) — always on"
                ),
                "note": (
                    "language and audience are applied per-connection AFTER "
                    "verification; unconfigured translator serves original "
                    "text labelled translation=original"
                ),
            },
        },
        "staged": {
            "event_hubs": "described in docs/CLAIMS.md — stream is in-process SSE",
            "azure_speech": "spoken-word audio track staged; text AD feed is live",
        },
        "sessions": sessions,
    }
