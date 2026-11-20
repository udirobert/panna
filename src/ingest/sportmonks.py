"""Sportmonks adapter — a real fixture payload mapped onto the event ledger.

The synthetic engine was the demo; this is the swap-in seam for licensed
data (post-hackathon real-data pilot — Sportmonks fixtures start at €29/mo).
Two paths, same mapping:

- ``to_events(payload)`` — pure: a fixture payload dict → ``IngestResult``.
  No network; the tests run entirely on a canned payload.
- ``fetch(fixture_id)`` — pulls ``fixtures/{id}?include=events;participants``
  with ``SPORTMONKS_API_TOKEN``, then maps it. Fail-soft: returns None on
  any upstream problem so callers degrade like the rest of the stack.

Honesty rules baked in:

- Basic-tier events carry **no coordinates**. Positions are set to pitch
  centre and flagged ``metadata["position_estimated"]=True`` — the AD
  describer drops directional wording for flagged events rather than
  narrating a channel it doesn't know.
- Stats the provider doesn't give (per-shot xG) are **not synthesized**.
  Reported team-level expected goals (when the fixture's statistics
  include them) go into ``provenance.reported_xg`` so a reader can
  compare measured-vs-derived; nothing is smeared onto events.
- Unknown event types are skipped but **counted** in
  ``provenance.unmapped_types`` — silence would hide data loss.

Own-goal attribution: Sportmonks credits an own goal to the *conceding*
side; the ledger records it under the *beneficiary* team (the side the
goal counts for) with ``metadata["own_goal"]=True`` and the conceding
player in ``metadata["conceded_by"]``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx

from src.events.schema import Event, EventType, Position, Team
from src.ingest.cache import read as _cache_read
from src.ingest.cache import write as _cache_write

_DEFAULT_BASE = "https://api.sportmonks.com/v3/football"
_CENTER = Position(x=60.0, y=40.0)  # pitch centre = "position unknown"


@dataclass
class IngestResult:
    events: list[Event]
    provenance: dict[str, Any] = field(default_factory=dict)


class SportmonksAdapter:
    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self.token = os.getenv("SPORTMONKS_API_TOKEN", "")
        self.base = os.getenv("SPORTMONKS_BASE", _DEFAULT_BASE).rstrip("/")
        self._http = httpx.Client(transport=transport, timeout=15.0)

    def fetch(self, fixture_id: int | str, refresh: bool = False) -> IngestResult | None:
        """Live path — pull a fixture payload, then map. None on failure.
        Cached briefly (see cache.TTL) — a live fixture's timeline updates."""
        if not self.token:
            return None
        try:
            data = None if refresh else _cache_read("sportmonks", f"fixture_{fixture_id}")
            source = "cache"
            if data is None:
                resp = self._http.get(
                    f"{self.base}/fixtures/{fixture_id}",
                    params={
                        "api_token": self.token,
                        "include": "events;participants;statistics",
                    },
                )
                resp.raise_for_status()
                data = resp.json().get("data") or {}
                _cache_write("sportmonks", f"fixture_{fixture_id}", data)
                source = "live"
            data.setdefault("_fixture_id", fixture_id)
            result = self.to_events(data)
            result.provenance["fetch_source"] = {"fixture": source}
            return result
        except Exception:  # noqa: BLE001 — fail-soft like the rest of the stack
            return None

    # ── mapping (pure) ──────────────────────────────────────────────────

    def to_events(self, fixture: dict[str, Any]) -> IngestResult:
        participants = {p["id"]: p for p in fixture.get("participants", []) if isinstance(p, dict)}
        team_of = {}
        names = {}
        for pid, p in participants.items():
            loc = (p.get("meta") or {}).get("location") or ""
            team_of[pid] = Team.HOME if loc == "home" else Team.AWAY
            names[pid] = p.get("name")

        events: list[Event] = []
        unmapped: dict[str, int] = {}
        for i, ev in enumerate(fixture.get("events", [])):
            if not isinstance(ev, dict):
                continue
            mapped = self._map_event(ev, i, team_of)
            if mapped is None:
                tname = self._type_name(ev)
                unmapped[tname] = unmapped.get(tname, 0) + 1
                continue
            events.append(mapped)

        events.sort(key=lambda e: e.timestamp_seconds)
        match_id = str(fixture.get("_fixture_id") or fixture.get("id") or "fixture")
        for i, e in enumerate(events):
            e.id = f"sm_{match_id}_{i:04d}"
            e.match_id = match_id

        reported_xg = self._reported_xg(fixture, team_of)
        return IngestResult(
            events=events,
            provenance={
                "provider": "sportmonks",
                "fixture_id": match_id,
                "home_team": names.get(next((p for p, t in team_of.items() if t == Team.HOME), -1)),
                "away_team": names.get(next((p for p, t in team_of.items() if t == Team.AWAY), -1)),
                "positions_estimated": True,
                "reported_xg": reported_xg,
                "unmapped_types": unmapped,
                "events_mapped": len(events),
                "events_skipped": sum(unmapped.values()),
            },
        )

    def _map_event(self, ev: dict[str, Any], idx: int, team_of: dict[int, Team]) -> Event | None:
        tname = self._type_name(ev)
        minute = min(int(ev.get("minute") or 0) + int(ev.get("extra_minute") or 0), 120)
        pid = ev.get("participant_id")
        team = team_of.get(pid, Team.HOME)
        player = ev.get("player_name") or "Unknown"
        meta: dict[str, Any] = {
            "source": "sportmonks",
            "provider_event_id": ev.get("id"),
            "position_estimated": True,
            "provider_type": tname,
        }

        if tname in ("goal", "penalty", "own goal", "owngoal"):
            outcome = "goal"
            if tname == "penalty":
                outcome = "penalty"
            elif tname in ("own goal", "owngoal"):
                outcome = "own_goal"
                meta["own_goal"] = True
                meta["conceded_by"] = player
                # the goal counts for the *other* team
                team = Team.AWAY if team == Team.HOME else Team.HOME
            if ev.get("related_player_name"):
                meta["assist"] = ev["related_player_name"]
            etype, out = EventType.GOAL, outcome
        elif tname == "missed penalty":
            etype, out = EventType.SHOT, "penalty_missed"
        elif tname == "substitution":
            etype, out = EventType.SUBSTITUTION, "sub"
            meta["player_in"] = ev.get("related_player_name")
        elif tname in ("yellowcard", "yellow card"):
            etype, out = EventType.FOUL, "yellow"
            meta["card"] = "yellow"
        elif tname in ("redcard", "red card", "secondyellow", "second yellow"):
            etype, out = EventType.FOUL, "red"
            meta["card"] = "red"
        elif tname in ("corner", "corner kick"):
            etype, out = EventType.SET_PIECE, "corner"
            meta["set_piece_type"] = "corner"
        elif tname == "penalty shootout":
            return None  # post-match, not broadcast timeline
        else:
            return None

        return Event(
            id=f"sm_tmp_{idx}",
            match_id="",
            minute=minute,
            second=0,
            type=etype,
            player=player,
            team=team,
            position=_CENTER,
            outcome=out,
            metadata=meta,
        )

    def _type_name(self, ev: dict[str, Any]) -> str:
        """Prefer the human-readable type name over numeric ids — ids shift
        across Sportmonks plan tiers, names are stable."""
        t = ev.get("type")
        if isinstance(t, dict) and t.get("name"):
            return str(t["name"]).lower()
        name = ev.get("type_name") or ev.get("name")
        return str(name).lower() if name else f"type_id:{ev.get('type_id')}"

    def _reported_xg(self, fixture: dict[str, Any], team_of: dict[int, Team]) -> dict | None:
        """Team-level expected goals from fixture statistics, when the plan
        tier includes them. Returned for provenance only — never smeared
        onto individual events."""
        out: dict[str, float] = {}
        for s in fixture.get("statistics", []):
            if not isinstance(s, dict):
                continue
            name = str((s.get("type") or {}).get("name") or s.get("type_name") or "").lower()
            if "expected" not in name and "xg" not in name:
                continue
            team = team_of.get(s.get("participant_id"))
            val = s.get("value") or (s.get("data") or {}).get("value")
            if team is not None and isinstance(val, int | float):
                out[team.value.lower()] = float(val)
        return out or None
