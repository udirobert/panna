"""StatsBomb open-data adapter — real event-level data → the panna ledger.

StatsBomb's open dataset (CC-BY 4.0, github.com/statsbomb/open-data) is the
free real-data path: no key, event-level detail, and a 120×80 pitch — the
exact coordinate space panna's `Position` already uses. Events arrive with
*measured* positions and `statsbomb_xg`, so `position_estimated` is only set
when the provider genuinely lacks a location.

Two paths, same mapping:

- ``to_events(events, home, away, match_id)`` — pure: an events-file list +
  team names → ``IngestResult``. No network.
- ``fetch(competition_id, season_id, match_id)`` — pulls the match record
  (for home/away names) + the events file over HTTPS, then maps. Fail-soft
  to None like the rest of the stack.

Well-known free fixtures (competition_id, season_id): World Cup 2018
(43, 3 — final is match 8658), La Liga Messi era (11, *), WSL (37, *).

Honesty rules:

- Measured stats stay measured: ``metadata.xg_provider`` carries
  ``statsbomb_xg`` verbatim; the derived xG model still runs for verifier
  consistency, and provenance aggregates the provider values so a reader
  can compare measured vs modelled.
- Own goals arrive as a pair ("Own Goal For" = beneficiary side, no player;
  "Own Goal Against" = conceder). The ledger keeps one goal — credited to
  the beneficiary with ``conceded_by`` resolved from the pair.
- Assists resolve through ``shot.key_pass_id`` → the passer's name.
- Unmapped StatsBomb types are skipped but counted in
  ``provenance.unmapped_types``.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from src.events.schema import Event, EventType, Position, Team
from src.ingest.cache import read as _cache_read
from src.ingest.cache import write as _cache_write
from src.ingest.sportmonks import IngestResult

_BASE = os.getenv(
    "STATSBOMB_BASE",
    "https://raw.githubusercontent.com/statsbomb/open-data/master/data",
).rstrip("/")
_CENTER = Position(x=60.0, y=40.0)

_SHOT_OUTCOME = {
    "Goal": "goal",
    "Saved": "on_target",
    "Saved To Post": "on_target",
    "Blocked": "blocked",
    "Off T": "off_target",
    "Post": "off_target",
    "Wayward": "off_target",
    "Saved Off Target": "off_target",
}
_BODY_PART = {
    "Right Foot": "right_foot",
    "Left Foot": "left_foot",
    "Head": "head",
}
_CARD = {
    "Yellow Card": "yellow",
    "Red Card": "red",
    "Second Yellow": "red",
}


def _pos(loc: list | tuple | None) -> Position | None:
    if not isinstance(loc, list | tuple) or len(loc) < 2:
        return None
    try:
        return Position(
            x=max(0.0, min(120.0, float(loc[0]))),
            y=max(0.0, min(80.0, float(loc[1]))),
        )
    except (TypeError, ValueError):
        return None


def _elapsed_seconds(e: dict[str, Any]) -> tuple[int, int]:
    """Timestamp "MM:SS.mmm" is cumulative elapsed — parse it rather than
    trusting minute/second fields (stoppage conventions differ)."""
    ts = e.get("timestamp")
    if isinstance(ts, str):
        try:
            mm, rest = ts.split(":", 1)
            ss = int(float(rest))
            return min(int(mm), 120), min(max(ss, 0), 59)
        except (ValueError, IndexError):
            pass
    return min(int(e.get("minute") or 0), 120), min(int(e.get("second") or 0), 59)


class StatsBombAdapter:
    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._http = httpx.Client(transport=transport, timeout=30.0)

    # ── live fetch (free, no key) ───────────────────────────────────────

    def fetch(
        self, competition_id: int, season_id: int, match_id: int, refresh: bool = False
    ) -> IngestResult | None:
        try:
            source: dict[str, str] = {}
            mkey = f"{competition_id}_{season_id}"
            matches = None if refresh else _cache_read("statsbomb-matches", mkey)
            if matches is None:
                matches = self._http.get(
                    f"{_BASE}/matches/{competition_id}/{season_id}.json"
                ).json()
                _cache_write("statsbomb-matches", mkey, matches)
                source["matches"] = "live"
            else:
                source["matches"] = "cache"
            meta = next((m for m in matches if m["match_id"] == match_id), None)
            if meta is None:
                return None
            events = None if refresh else _cache_read("statsbomb-events", match_id)
            if events is None:
                events = self._http.get(f"{_BASE}/events/{match_id}.json").json()
                _cache_write("statsbomb-events", match_id, events)
                source["events"] = "live"
            else:
                source["events"] = "cache"
            result = self.to_events(
                events,
                home=meta["home_team"]["home_team_name"],
                away=meta["away_team"]["away_team_name"],
                match_id=str(match_id),
            )
            result.provenance["fetch_source"] = source
            return result
        except Exception:  # noqa: BLE001 — fail-soft
            return None

    # ── mapping (pure) ──────────────────────────────────────────────────

    def to_events(
        self,
        events: list[dict[str, Any]],
        home: str,
        away: str,
        match_id: str = "sb_match",
    ) -> IngestResult:
        by_id = {e.get("id"): e for e in events if isinstance(e, dict)}
        # the conceder of an own goal lives on the paired "Own Goal Against"
        og_conceders = {
            (e.get("timestamp"), e.get("period")): (e.get("player") or {}).get("name")
            for e in events
            if (e.get("type") or {}).get("name") == "Own Goal Against"
        }
        team_name = {home: Team.HOME, away: Team.AWAY}
        xg_totals = {Team.HOME: 0.0, Team.AWAY: 0.0}
        out_events: list[Event] = []
        unmapped: dict[str, int] = {}
        positions_estimated = False

        for i, e in enumerate(events):
            if not isinstance(e, dict):
                continue
            tname = str((e.get("type") or {}).get("name") or "unknown")
            detail = e.get(
                {
                    "Shot": "shot",
                    "Pass": "pass",
                    "Carry": "carry",
                    "Duel": "duel",
                    "Interception": "interception",
                    "Foul Committed": "foul_committed",
                    "Substitution": "substitution",
                    "Tactical Shift": "tactical_shift",
                }.get(tname, ""),
                {},
            )
            team = team_name.get((e.get("team") or {}).get("name"))
            if team is None:
                unmapped[tname] = unmapped.get(tname, 0) + 1
                continue
            player = (e.get("player") or {}).get("name") or "Unknown"
            minute, second = _elapsed_seconds(e)
            pos = _pos(e.get("location"))
            meta: dict[str, Any] = {
                "source": "statsbomb-open-data",
                "provider_event_id": e.get("id"),
                "provider_type": tname,
            }

            if tname == "Shot":
                outcome = _SHOT_OUTCOME.get(
                    str((detail.get("outcome") or {}).get("name") or ""), "off_target"
                )
                etype = EventType.SHOT
                if outcome == "goal":
                    etype = EventType.GOAL
                    if (detail.get("type") or {}).get("name") == "Penalty":
                        outcome = "penalty"
                    assist = by_id.get(detail.get("key_pass_id"))
                    if assist:
                        meta["assist"] = (assist.get("player") or {}).get("name")
                xg = detail.get("statsbomb_xg")
                if isinstance(xg, int | float):
                    meta["xg_provider"] = float(xg)
                    xg_totals[team] += float(xg)
                meta["body_part"] = _BODY_PART.get(
                    str((detail.get("body_part") or {}).get("name") or ""), "other"
                )
            elif tname == "Own Goal For":
                etype, outcome = EventType.GOAL, "own_goal"
                meta["own_goal"] = True
                conceded = og_conceders.get((e.get("timestamp"), e.get("period")))
                meta["conceded_by"] = conceded
                if conceded and player == "Unknown":
                    player = conceded  # the conceder is the story of an own goal
            elif tname == "Pass":
                etype = EventType.PASS
                outcome = "complete" if not detail.get("outcome") else "incomplete"
            elif tname == "Carry":
                etype = EventType.CARRY
                outcome = "carry"
            elif tname == "Duel" and str((detail.get("type") or {}).get("name")) == "Tackle":
                etype = EventType.TACKLE
                outcome = (
                    "success"
                    if "Won" in str((detail.get("outcome") or {}).get("name") or "")
                    or "Success" in str((detail.get("outcome") or {}).get("name") or "")
                    else "fail"
                )
            elif tname == "Interception":
                etype, outcome = EventType.INTERCEPTION, "interception"
            elif tname == "Pressure":
                etype, outcome = EventType.PRESSURE, "pressure"
            elif tname == "Foul Committed":
                etype = EventType.FOUL
                card = _CARD.get(str((detail.get("card") or {}).get("name") or ""))
                if card:
                    meta["card"] = card
                    if (detail.get("card") or {}).get("name") == "Second Yellow":
                        meta["card_detail"] = "second_yellow"
                outcome = card or "foul"
            elif tname == "Substitution":
                etype, outcome = EventType.SUBSTITUTION, "sub"
                meta["player_in"] = (detail.get("replacement") or {}).get("name")
            elif tname == "Tactical Shift":
                etype, outcome = EventType.FORMATION_CHANGE, "shift"
                meta["formation"] = detail.get("formation")
            else:
                unmapped[tname] = unmapped.get(tname, 0) + 1
                continue

            if pos is None:
                pos = _CENTER
                meta["position_estimated"] = True
                positions_estimated = True
            if e.get("under_pressure"):
                meta["under_pressure"] = True

            end_loc = detail.get("end_location") if isinstance(detail, dict) else None
            out_events.append(
                Event(
                    id=f"sb_tmp_{i}",
                    match_id="",
                    minute=minute,
                    second=second,
                    type=etype,
                    player=player,
                    team=team,
                    position=pos,
                    end_location=_pos(end_loc),
                    outcome=outcome,
                    metadata=meta,
                )
            )

        out_events.sort(key=lambda ev: ev.timestamp_seconds)
        for i, e in enumerate(out_events):
            e.id = f"sb_{match_id}_{i:04d}"
            e.match_id = match_id

        return IngestResult(
            events=out_events,
            provenance={
                "provider": "statsbomb-open-data",
                "license": "CC-BY-4.0",
                "match_id": match_id,
                "home_team": home,
                "away_team": away,
                "positions_estimated": positions_estimated,
                "reported_xg": {
                    "home": round(xg_totals[Team.HOME], 3),
                    "away": round(xg_totals[Team.AWAY], 3),
                },
                "unmapped_types": unmapped,
                "events_mapped": len(out_events),
                "events_skipped": sum(unmapped.values()),
            },
        )
