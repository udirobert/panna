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
from src.events.frames import event_frame
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
                event_frame(e),
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

    # producer gate + cost guard (the winners' patterns)
    approved: set[str] = field(default_factory=set)  # held items cleared by a human
    killed: set[str] = field(default_factory=set)  # items a producer killed outright
    viewers: int = 0
    auto_paused: bool = False  # matchday pauses when nobody watches — no wasted tokens

    def __post_init__(self) -> None:
        self.timeline = _build_timeline(self.events, self.result)
        self.momentum_series = _build_momentum_series(self.events)
        self._cursor = 0
        self._minute_cursor = 0
        self._pending: list[Item] = []
        self._approvals_pending: list[Item] = []
        self._last_advance = time.monotonic()
        # per-match translation cache shared by every connected feed so two
        # viewers in the same language never pay twice for the same line
        self.translation_cache: dict[tuple[str, str], str] = {}
        self.events_by_id = {e.id: e for e in self.events}

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

    # ---- producer gate ------------------------------------------------------

    @staticmethod
    def _item_id(kind: str, payload: dict) -> str:
        return str(payload.get("id") or f"{kind}:{payload.get('minute')}")

    def _held(self, kind: str, payload: dict) -> bool:
        """An insight/commentary whose verifier rejected it stays off air
        until a producer approves it (or kills it outright). Fails closed."""
        if kind not in ("insight", "commentary"):
            return False
        pid = self._item_id(kind, payload)
        if pid in self.approved:
            return False
        v = payload.get("verification") or {}
        return v.get("status") == "rejected"

    def _airable(self, kind: str, payload: dict) -> bool:
        if kind not in ("insight", "commentary"):
            return True
        return self._item_id(kind, payload) not in self.killed and not self._held(kind, payload)

    def board(self) -> list[dict]:
        """The producer console: every broadcast line with its verdict."""
        rows = []
        for at, kind, _, payload in self.timeline:
            if kind not in ("insight", "commentary"):
                continue
            pid = self._item_id(kind, payload)
            v = payload.get("verification") or {}
            if pid in self.killed:
                air = "killed"
            elif self._held(kind, payload):
                air = "held"
            elif at <= self.clock:
                air = "aired"
            else:
                air = "queued"
            rows.append(
                {
                    "id": pid,
                    "kind": kind,
                    "at": at,
                    "text": payload.get("claim") or payload.get("text") or "",
                    "air_status": air,
                    "verdict": v.get("status"),
                    "reason": v.get("reason"),
                    "checks": v.get("checks") or [],
                }
            )
        rows.sort(key=lambda r: r["at"])
        return rows

    def decide(self, item_id: str, decision: str) -> dict:
        """Approve a held line (it airs at the next beat) or kill it for good."""
        if decision == "approve":
            self.approved.add(item_id)
            self.killed.discard(item_id)
            # if its slot already passed, flush it on the next advance
            for at, kind, owner, payload in self.timeline[: self._cursor]:
                if kind in ("insight", "commentary") and self._item_id(kind, payload) == item_id:
                    self._approvals_pending.append((at, kind, owner, payload))
            return {"id": item_id, "air_status": "approved"}
        if decision == "kill":
            self.killed.add(item_id)
            self.approved.discard(item_id)
            return {"id": item_id, "air_status": "killed"}
        raise ValueError(f"decision must be approve|kill, got {decision!r}")

    def seed_bad_claim(self) -> dict:
        """Red-team demo: inject a fabricated line and watch the gate refuse it.

        Plants a false score and an invented stat, runs them through the real
        Verifier, and inserts them into the timeline — where they land in the
        producer's hold queue instead of on screen.
        """
        from src.agents.verifier import VerifierAgent, _Facts  # noqa: PLC0415

        facts = _Facts(self.events)
        verifier = VerifierAgent()
        minute = min(int(self.clock // 60), 89)
        h, a = facts.score_at(minute)
        bad_score = f"{h + 1}-{a}" if h < 9 else f"{h}-{a + 1}"

        from src.events.schema import CommentaryEntry, Insight  # noqa: PLC0415

        planted = Insight(
            id=f"ins_planted_{int(self.clock)}",
            type="narrative",
            claim=f"Home have created {facts.home_xg * 1.5 + 2.37:.2f} xG of pressure",
            value=facts.home_xg * 1.5 + 2.37,
            confidence=0.9,
            evidence=[],
            agent="analyst",
            timestamp=f"{minute}:00",
        )
        v_ins = verifier.verify_insight(planted, self.events, facts)
        planted.verification = v_ins
        insd = planted.model_dump()
        insd["reveal_minute"] = minute

        entry = CommentaryEntry(
            id=f"com_planted_{int(self.clock)}",
            minute=minute,
            second=0,
            text=f"And it's {bad_score} now as the pressure tells!",
            insight_ids=[planted.id],
        )
        v_com = verifier.verify_commentary(entry, self.events, {planted.id: v_ins}, facts)
        entry.verification = v_com
        cd = entry.model_dump()

        at = float(self.clock + 2)
        self.timeline.append((at, "insight", "analyst", insd))
        self.timeline.append((at + 1, "commentary", "commentator", cd))
        self.timeline.sort(key=lambda it: it[0])
        return {
            "planted": [insd["claim"], cd["text"]],
            "verdicts": {
                planted.id: v_ins.model_dump(),
                entry.id: v_com.model_dump(),
            },
        }

    # ---- cost guard -----------------------------------------------------------

    def add_viewer(self) -> None:
        self.viewers += 1
        if self.auto_paused:
            self.auto_paused = False
            self.play()

    def remove_viewer(self) -> None:
        self.viewers = max(0, self.viewers - 1)
        if self.viewers == 0 and self.playing:
            # nobody watching → the matchday pauses; agents stop spending
            self.pause()
            self.auto_paused = True

    # ---- playback ---------------------------------------------------------

    def advance(self) -> list[tuple[str, dict]]:
        """Advance the clock by real elapsed time × speed; return due frames."""
        now = time.monotonic()
        dt = now - self._last_advance
        self._last_advance = now
        frames: list[tuple[str, dict]] = []
        if self.playing:
            self.clock = min(self.clock + dt * self.speed, float(MATCH_SECONDS))

        # approvals flush: a held line the producer cleared airs immediately
        for _, kind, _, payload in self._approvals_pending:
            frames.append((kind, {**payload, "approved": True}))
        self._approvals_pending = []

        # raw event batch (always live, even while specialists are degraded)
        batch: list[dict] = []
        while self._cursor < len(self.timeline) and self.timeline[self._cursor][0] <= self.clock:
            at, kind, owner, payload = self.timeline[self._cursor]
            self._cursor += 1
            if owner and owner in self.failed:
                self._pending.append((at, kind, owner, payload))
                continue
            if not self._airable(kind, payload):
                continue  # held by the verifier gate or killed by the producer
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
        held: list[dict] = []
        events_so_far: list[dict] = []
        for _at, kind, _owner, payload in self.timeline[: self._cursor]:
            if kind == "event":
                events_so_far.append(payload)
            elif kind in revealed:
                if self._airable(kind, payload):
                    revealed[kind].append(payload)
                elif self._held(kind, payload) and self._item_id(kind, payload) not in self.killed:
                    held.append(payload)
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
            "reasoning_source": self.result.get("reasoning_source", "template"),
            "reasoning_model": self.result.get("reasoning_model"),
            "reasoning_tool_calls": self.result.get("reasoning_tool_calls", 0),
            "events": events_so_far,
            "key_moments": revealed["detection"],
            "insights": revealed["insight"],
            "commentary": revealed["commentary"],
            "held": held,
            "verification": self.result.get("verification", {}),
            "viewers": self.viewers,
            "auto_paused": self.auto_paused,
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
_BUILD_LOCKS: dict[str, Any] = {}
_LOCKS_GUARD: Any = None


def _build_lock(match_id: str) -> Any:
    global _LOCKS_GUARD
    import threading

    if _LOCKS_GUARD is None:
        _LOCKS_GUARD = threading.Lock()
    with _LOCKS_GUARD:
        lock = _BUILD_LOCKS.get(match_id)
        if lock is None:
            lock = threading.Lock()
            _BUILD_LOCKS[match_id] = lock
        return lock


def get_or_create_session(
    match_id: str,
    events: list[Event],
    *,
    seed: int = 42,
    home_team: str = "Home FC",
    away_team: str = "Away United",
) -> MatchSession:
    """Return the live session for a match, rebuilding if the events changed.

    Building runs the agent pipeline (which may call Foundry) and is
    serialized per match so concurrent viewers never pay for it twice. Call
    this from a worker thread when the Foundry path is live.
    """
    existing = _SESSIONS.get(match_id)
    if existing is not None and existing.events is events:
        return existing
    with _build_lock(match_id):
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


def session_for(match_id: str, events: list[Event]) -> MatchSession | None:
    """Cheap lookup: the session for this exact event set, or None.

    Call from the async stream path first so the (possibly Foundry-backed)
    build can be scheduled on a worker thread instead of blocking the loop.
    """
    existing = _SESSIONS.get(match_id)
    return existing if existing is not None and existing.events is events else None
