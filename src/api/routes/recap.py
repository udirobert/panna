from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.routes.matches import _CONFIGS, _MATCHES
from src.foundry import narrative
from src.models.xg import event_xg

router = APIRouter()


def _score(events) -> tuple[int, int]:
    home = away = 0
    for e in events:
        if e.type.value == "goal":
            if e.team.value == "Home":
                home += 1
            else:
                away += 1
    return home, away


@router.get("/{match_id}")
def get_recap(match_id: str) -> dict:
    """Post-match case file.

    Foundry-backed when credentials are configured (GPT-5.4 editorial verdict);
    deterministic template recap otherwise. Always returns the structured
    exhibits so the frontend renders the same case layout either way.
    """
    if match_id not in _MATCHES:
        raise HTTPException(404, "match not found")
    events = _MATCHES[match_id]
    cfg = _CONFIGS.get(match_id)

    from src.agents.director import DirectorAgent

    result = DirectorAgent().run({"events": events})
    insights = result["insights"]
    key_moments = result["key_moments"]

    verdict = narrative.verdict_recap(match_id, insights, key_moments)
    home, away = _score(events)
    home_xg = away_xg = 0.0
    for e in events:
        if e.type.value in ("shot", "goal"):
            xg = event_xg(e) or float(e.metadata.get("xg", 0.0))
            if e.team.value == "Home":
                home_xg += xg
            else:
                away_xg += xg
    team_by_event = {e.id: e.team.value for e in events}
    top = sorted(insights, key=lambda i: i.confidence, reverse=True)[:4]
    goals = [km for km in key_moments if km.type == "goal"]

    # formation timeline: kickoff + every formation change, per side
    kickoff = {
        "home": cfg.home_formation if cfg else "4-3-3",
        "away": cfg.away_formation if cfg else "4-4-2",
    }
    current = dict(kickoff)
    evolution: list[dict] = []
    for e in events:
        if e.type.value == "formation_change" and e.metadata.get("formation"):
            side = e.metadata.get("side")
            if side not in ("home", "away"):
                side = "home" if e.team.value == "Home" else "away"
            current[side] = e.metadata["formation"]
            if e.minute > 0:
                evolution.append(
                    {"minute": e.minute, "side": side, "formation": e.metadata["formation"]}
                )

    return {
        "match_id": match_id,
        "verdict": verdict["result"]
        if isinstance(verdict["result"], str)
        else str(verdict["result"]),
        "source": verdict["source"],
        "model": verdict["model"],
        "status": verdict["status"],
        "structured": {
            "home_team": cfg.home_team if cfg else "Home FC",
            "away_team": cfg.away_team if cfg else "Away United",
            "score": {"home": home, "away": away},
            "xg": {"home": round(home_xg, 2), "away": round(away_xg, 2)},
            "formations": {
                "kickoff": kickoff,
                "final": current,
                "evolution": evolution,
            },
            "goals": [
                {
                    "minute": g.minute,
                    "team": team_by_event.get(g.event_id, "Home"),
                    "description": g.description,
                }
                for g in goals
            ],
            "exhibits": [
                {
                    "type": i.type,
                    "claim": i.claim,
                    "confidence": i.confidence,
                    "evidence": i.evidence,
                }
                for i in top
            ],
        },
    }
