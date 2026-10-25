"""Match replay session: a controllable broadcast clock over computed pipeline output.

The agent pipeline is batch (deterministic, local). The session turns it into a
*live* broadcast: one shared clock per match that the frontend can play, pause,
scrub and rewind. All intelligence arrives as timed frames on that clock.

Failure injection darkens a specialist cluster: its output is buffered while
degraded and flushed on recovery with ``recovered: true`` — stigmergy on screen
(the traces stay; peers finish the work).
"""

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field
from typing import Any

from src.agents.director import DirectorAgent
from src.events.schema import Event, Team

MATCH_SECONDS = 90 * 60  # replay window ends at full time (90')

# timeline item: (at_seconds, kind, owner, payload)
# owner: which specialist produces it (for failure buffering); "" = raw feed
Item = tuple[float, str, str, dict]

_AGENT_OWNER = {"detection": "scout", "insight": "analyst", "commentary": "commentator"}


def _build_momentum_series(events: list[Event]) -> dict[str, list[float]]:
    """Per-minute danger (max shot xG) and cumulative xG race, BBC-style."""
    home_danger = [0.0] * 91
    away_danger = [0.0] * 91
    home_cum = [0.0] * 91
    away_cum = [0.0] * 91
    for e in events:
        if e.type.value not in ("shot", "goal"):
            continue
        xg = float(e.metadata.get("xg", 0.0))
        m = min(e.minute, 90)
        if e.team == Team.HOME:
            home_danger[m] = max(home_danger[m], xg)
        else:
            away_danger[m] = max(away_danger[m], xg)
    running_h = running_a = 0.0
    for m in range(91):
        running_h += home_danger[m]
        running_a += away_danger[m]
        home_cum[m] = round(running_h, 3)
        away_cum[m] = round(running_a, 3)
    return {
        "home_danger": [round(v, 3) for v in home_danger],
        "away_danger": [round(v, 3) for v in away_danger],
        "home_cum": home_cum,
        "away_cum": away_cum,
    }


def _build_timeline(events: list[Event], result: dict[str, Any]) -> list[Item]:
    """Merge raw events + key moments + insights + commentary into one timed feed."""
    items: list[Item] = []
    ev_minute = {e.id: e.minute for e in events}

    for e in events:
        items.append(
            (
                float(e.timestamp_seconds),
                "event",
                "",
                {
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
                },
            )
        )

    for km in result.get("key_moments", []):
        kmd = km.model_dump() if hasattr(km, "model_dump") else dict(km)
        items.append((float(kmd["minute"] * 60 + 5), "detection", "scout", kmd))

    for ins in result.get("insights", []):
        insd = ins.model_dump() if hasattr(ins, "model_dump") else dict(ins)
        # reveal the insight when its latest evidence event has happened
        evidence = insd.get("evidence") or []
        reveal = max((ev_minute.get(eid, 0) for eid in evidence), default=45)
        insd["reveal_minute"] = reveal
        items.append((float(reveal * 60 + 10), "insight", "analyst", insd))

    for c in result.get("commentary", []):
        cd = c.model_dump() if hasattr(c, "model_dump") else dict(c)
        at = min(MATCH_SECONDS, cd["minute"] * 60 + cd.get("second", 0) + 8)
        items.append((float(at), "commentary", "commentator", cd))

    # goals as broadcast moments with running score
    home = away = 0
    for e in events:
        if e.type.value == "goal":
            if e.team == Team.HOME:
                home += 1
            else:
                away += 1
            items.append(
                (
                    float(e.timestamp_seconds),
                    "goal",
                    "",
                    {
                        "minute": e.minute,
                        "team": e.team.value,
                        "player": e.player,
                        "home_score": home,
                        "away_score": away,
                        "xg": e.metadata.get("xg"),
                        "x": e.position.x,
                        "y": e.position.y,
                    },
                )
            )

    items.sort(key=lambda it: it[0])
    return items


@dataclass
class MatchSession:
    match_id: str
    seed: int
    home_team: str
    away_team: str
    events: list[Event]
    result: dict[str, Any]
    timeline: list[Item] = field(init=False)
    momentum_series: dict[str, list[float]] = field(init=False)

    # playback state
    clock: float = 0.0
    speed: float = 60.0  # match-seconds per real second (90 min match ≈ 90 s demo)
    playing: bool = False
    epoch: int = 0  # bumped on seek/reset; SSE clients re-snapshot
    autoplay_pending: bool = True  # first stream connection starts playback

    # failure choreography
    failed: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.timeline = _build_timeline(self.events, self.result)
        self.momentum_series = _build_momentum_series(self.events)
        self._cursor = 0
        self._minute_cursor = 0
        self._pending: list[Item] = []
        self._last_advance = time.monotonic()

    # ---- control ----------------------------------------------------------

    def play(self) -> None:
        self.playing = True

    def pause(self) -> None:
        self.playing = False

    def seek(self, at_seconds: float) -> None:
        """Jump the clock (forward or back). Revealed state is recomputed."""
        self.clock = max(0.0, min(float(at_seconds), float(MATCH_SECONDS)))
        self._cursor = 0
        while self._cursor < len(self.timeline) and self.timeline[self._cursor][0] <= self.clock:
            self._cursor += 1
        self._minute_cursor = int(self.clock // 60) + 1
        self._pending = []
        self.playing = self.playing and self.clock < MATCH_SECONDS
        self.epoch += 1

    def set_speed(self, speed: float) -> None:
        self.speed = max(1.0, min(float(speed), 3600.0))

    def fail(self, agent: str) -> None:
        if agent in _AGENT_OWNER.values():
            self.failed.add(agent)

    def recover(self, agent: str) -> None:
        self.failed.discard(agent)

    # ---- playback ---------------------------------------------------------

    def advance(self) -> list[tuple[str, dict]]:
        """Advance the clock by real elapsed time × speed; return due frames."""
        now = time.monotonic()
        dt = now - self._last_advance
        self._last_advance = now
        frames: list[tuple[str, dict]] = []
        if self.playing:
            self.clock = min(self.clock + dt * self.speed, float(MATCH_SECONDS))

        # raw event batch (always live, even while specialists are degraded)
        batch: list[dict] = []
        while self._cursor < len(self.timeline) and self.timeline[self._cursor][0] <= self.clock:
            at, kind, owner, payload = self.timeline[self._cursor]
            self._cursor += 1
            if owner and owner in self.failed:
                self._pending.append((at, kind, owner, payload))
                continue
            if kind == "event":
                batch.append(payload)
            else:
                frames.append((kind, payload))
        if batch:
            frames.insert(0, ("events", {"batch": batch}))

        # recovery flush: orphaned traces get finished by peers
        if self._pending:
            still = [it for it in self._pending if it[2] in self.failed]
            flushed = [it for it in self._pending if it[2] not in self.failed]
            self._pending = still
            for _, kind, _, payload in flushed:
                frames.append((kind, {**payload, "recovered": True}))

        # momentum point each match minute
        cur_minute = int(self.clock // 60)
        while self._minute_cursor <= min(cur_minute, 90):
            m = self._minute_cursor
            frames.append(
                (
                    "momentum",
                    {
                        "minute": m,
                        "home_cum": self.momentum_series["home_cum"][m],
                        "away_cum": self.momentum_series["away_cum"][m],
                        "home_danger": self.momentum_series["home_danger"][m],
                        "away_danger": self.momentum_series["away_danger"][m],
                    },
                )
            )
            self._minute_cursor += 1

        frames.append(
            (
                "clock",
                {
                    "t": int(self.clock),
                    "minute": int(self.clock // 60),
                    "second": int(self.clock % 60),
                    "speed": self.speed,
                    "playing": self.playing,
                    "failed": sorted(self.failed),
                },
            )
        )

        if self.playing and self.clock >= MATCH_SECONDS:
            self.playing = False
            frames.append(("full_time", self._score()))
        return frames

    # ---- state ------------------------------------------------------------

    def _score(self) -> dict[str, Any]:
        home = away = 0
        for at, kind, _, payload in self.timeline:
            if kind == "goal" and at <= self.clock:
                home, away = payload["home_score"], payload["away_score"]
        return {"home": home, "away": away}

    def score(self) -> dict[str, Any]:
        return self._score()

    def snapshot(self) -> dict[str, Any]:
        score = self._score()
        minute = int(self.clock // 60)
        revealed = {kind: [] for kind in ("detection", "insight", "commentary")}
        events_so_far: list[dict] = []
        for _at, kind, _owner, payload in self.timeline[: self._cursor]:
            if kind == "event":
                events_so_far.append(payload)
            elif kind in revealed:
                revealed[kind].append(payload)
        ms = self.momentum_series
        return {
            "match_id": self.match_id,
            "seed": self.seed,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "clock": int(self.clock),
            "minute": minute,
            "speed": self.speed,
            "playing": self.playing,
            "score": score,
            "failed": sorted(self.failed),
            "health": self.result.get("health", {}),
            "commentary_source": self.result.get("commentary_source", "template"),
            "events": events_so_far,
            "key_moments": revealed["detection"],
            "insights": revealed["insight"],
            "commentary": revealed["commentary"],
            "momentum": {
                "minutes": list(range(minute + 1)),
                "home_cum": ms["home_cum"][: minute + 1],
                "away_cum": ms["away_cum"][: minute + 1],
                "home_danger": ms["home_danger"][: minute + 1],
                "away_danger": ms["away_danger"][: minute + 1],
            },
        }


# ---- session registry ------------------------------------------------------

_SESSIONS: dict[str, MatchSession] = {}
_EPOCHS = itertools.count(1)  # globally monotonic so clients always resync


def get_or_create_session(
    match_id: str,
    events: list[Event],
    *,
    seed: int = 42,
    home_team: str = "Home FC",
    away_team: str = "Away United",
) -> MatchSession:
    """Return the live session for a match, rebuilding if the events changed."""
    existing = _SESSIONS.get(match_id)
    if existing is not None and existing.events is events:
        return existing
    result = DirectorAgent().run({"events": events})
    session = MatchSession(
        match_id=match_id,
        seed=seed,
        home_team=home_team,
        away_team=away_team,
        events=events,
        result=result,
    )
    session.epoch = next(_EPOCHS)
    _SESSIONS[match_id] = session
    return session


def drop_session(match_id: str) -> None:
    _SESSIONS.pop(match_id, None)


def get_session(match_id: str) -> MatchSession | None:
    return _SESSIONS.get(match_id)
