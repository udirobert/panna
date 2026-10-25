"""Shareable case-file poster.

``GET /share/{match_id}`` returns a standalone, self-contained HTML poster of the
match's full-time case: headline verdict, score, xG, decisive moments, and a
"replay this match" link carrying the seed. Because matches are deterministic per
seed, anyone who opens the link boots into the *exact* same match — the viral
primitive. No build step, no external assets, works from a plain file.
"""

from __future__ import annotations

import html
import os

from fastapi import APIRouter, HTTPException
from starlette.responses import HTMLResponse

from src.api.routes.matches import _CONFIGS, _MATCHES
from src.foundry import narrative
from src.models.xg import event_xg

router = APIRouter()

POSTER_CSS = """
*{box-sizing:border-box} body{margin:0;background:#07100d;color:#e8f2ec;
 font-family:'Segoe UI',system-ui,-apple-system,sans-serif;padding:24px}
 .poster{max-width:640px;margin:0 auto;border:1px solid rgba(245,197,66,.4);
 border-radius:12px;overflow:hidden;
 background:linear-gradient(180deg,rgba(245,197,66,.06),transparent 40%),#0a1712}
 .head{padding:20px 24px;border-bottom:1px solid rgba(235,250,240,.12)}
 .kicker{font-size:11px;letter-spacing:.26em;color:#f5c542;font-weight:700}
 .score{display:flex;align-items:baseline;gap:14px;margin-top:12px}
 .team{font-weight:800;letter-spacing:.06em;font-size:18px}
 .team.h{color:#38bdf8}.team.a{color:#f59e0b}
 .num{font-size:40px;font-weight:900;font-variant-numeric:tabular-nums}
 .verdict{padding:20px 24px;font-size:22px;font-weight:800;line-height:1.25}
 .story{padding:0 24px 18px;color:#d9e8df;font-size:14px;line-height:1.6}
 .xg{display:flex;gap:20px;padding:0 24px 18px;font-size:13px;color:#7d9187}
 .xg b{color:#e8f2ec}
 .exh{padding:4px 24px 18px;display:flex;flex-direction:column;gap:8px}
 .row{display:flex;gap:10px;font-size:13px}
 .tag{color:#f5c542;font-weight:800;width:26px;flex:none}
 .cta{display:block;margin:18px 24px 24px;padding:14px 18px;text-align:center;
 background:#f5c542;color:#141003;font-weight:800;border-radius:8px;text-decoration:none;
 letter-spacing:.06em;font-size:14px}
 .foot{padding:14px 24px;border-top:1px solid rgba(235,250,240,.1);font-size:11px;
 color:#7d9187;display:flex;justify-content:space-between;letter-spacing:.06em}
"""


def _score(events) -> tuple[int, int]:
    home = away = 0
    for e in events:
        if e.type.value == "goal":
            if e.team.value == "Home":
                home += 1
            else:
                away += 1
    return home, away


def _xg(events) -> tuple[float, float]:
    h = a = 0.0
    for e in events:
        if e.type.value in ("shot", "goal"):
            xg = event_xg(e) or float(e.metadata.get("xg", 0.0))
            if e.team.value == "Home":
                h += xg
            else:
                a += xg
    return round(h, 2), round(a, 2)


@router.get("/{match_id}", response_class=HTMLResponse)
def share(match_id: str) -> HTMLResponse:
    if match_id not in _MATCHES:
        raise HTTPException(404, "match not found")
    events = _MATCHES[match_id]
    from src.agents.director import DirectorAgent

    result = DirectorAgent().run({"events": events})
    insights = result["insights"]
    moments = result["key_moments"]
    home, away = _score(events)
    hx, ax = _xg(events)

    verdict = narrative.verdict_recap(match_id, insights, moments)
    story = verdict["result"] if isinstance(verdict["result"], str) else str(verdict["result"])

    home_name = html.escape(_team_name(match_id, "Home"))
    away_name = html.escape(_team_name(match_id, "Away"))
    top = sorted(insights, key=lambda i: i.confidence, reverse=True)[:4]
    goals = [m for m in moments if m.type == "goal"]

    headline = (
        f"FULL-TIME — {home}–{away}"
        if home == away
        else f"FULL-TIME — {home_name.upper()} WINS {home}-{away}"
    )

    rows = "".join(
        f'<div class="row"><span class="tag">E{i+1}</span>'
        f'<span>{html.escape(x.claim)} <span style="color:#7d9187">'
        f"({round(x.confidence*100)}% · {len(x.evidence)} evidence)</span></span></div>"
        for i, x in enumerate(top)
    )
    goal_rows = "".join(
        f'<div class="row"><span class="tag">{g.minute}&prime;</span>'
        f"<span>{html.escape(g.description)}</span></div>"
        for g in goals
    )
    # default to the local dev frontend; deploy sets FRONTEND_ORIGIN explicitly
    origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").rstrip("/")
    replay_url = f"{origin}/?match={match_id}"

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Panna — Case File {match_id}</title><style>{POSTER_CSS}</style></head>
<body><div class="poster">
 <div class="head"><div class="kicker">PANNA · THE VERDICT · CASE FILED</div>
  <div class="score"><span class="team h">{home_name}</span>
   <span class="num">{home} – {away}</span>
   <span class="team a">{away_name}</span></div></div>
 <div class="verdict">{html.escape(headline)}</div>
 <div class="story">{html.escape(story)}</div>
 <div class="xg"><span>xG <b>{hx}</b> – <b>{ax}</b></span>
   <span>key moments <b>{len(moments)}</b></span>
   <span>evidence <b>{sum(len(x.evidence) for x in top)}</b></span></div>
 <div class="exh">{goal_rows}{rows}</div>
 <a class="cta" href="{replay_url}">▶ REPLAY THIS MATCH</a>
 <div class="foot"><span>SYNTHETIC · FOOTBALL-REALISTIC DATA</span>
   <span>SEED {_seed_of(match_id)} · MICROSOFT FOUNDRY · MAF · AZURE</span></div>
</div></body></html>"""
    return HTMLResponse(doc)


def _team_name(match_id: str, which: str) -> str:
    cfg = _CONFIGS.get(match_id)
    if cfg:
        return cfg.home_team if which == "Home" else cfg.away_team
    return "HOME FC" if which == "Home" else "AWAY UNITED"


def _seed_of(match_id: str) -> int:
    if match_id.startswith("match_") and match_id[6:].isdigit():
        return int(match_id[6:])
    from src.api.routes.matches import _CONFIGS

    cfg = _CONFIGS.get(match_id)
    return cfg.seed if cfg else 42
