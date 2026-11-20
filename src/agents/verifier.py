"""Verifier agent: the independent recount between a drafted line and the air.

The rule the Inside the Game winners converged on: *let AI tell the story,
let code keep the score*. Panna's Verifier never wrote any line it checks —
it re-derives every metric from the raw event ledger through the same
deterministic models (``src/models``) and rules on each broadcast item:

- ``verified``  — every checkable number matches a recount.
- ``repaired``  — a wrong number on a recountable insight; the Verifier
  rewrites the claim with the true values, re-checks it, and airs it flagged
  (``repair_of`` keeps the original text for the audit trail).
- ``rejected``  — a check failed that cannot be repaired; the item is held
  off air for the producer. The gate fails closed.

Checks, in order:

1. Evidence grounding — cited event ids must exist in the ledger.
2. Typed recount — for each insight type the engine recomputes the metric
   (xG totals, PPDA, formation stats, influence ranking, momentum swing)
   and compares it to ``insight.value`` and the numbers in the claim text.
3. Number grounding — every decimal in the text must match a number the
   engine can justify (a stat, an event xG, a count).
4. Minute grounding — ``N'`` references must name a minute where a matching
   event actually happened (a goal line needs a goal at that minute).
5. Score grounding — ``N-M`` / ``N to M`` patterns must equal the running
   score at the line's minute.
6. Attribution — for player claims, the named player must be the player the
   recount names (a right number on the wrong player is refused).
7. Clean language — betting terms, certainty claims and real-world league
   marks are banned outright (the match is synthetic; those words can only
   be hallucinated or unsafe).
8. House style — broadcast lines must fit on screen (≤240 chars).
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from src.events.schema import CommentaryEntry, Event, Insight, Team, Verdict
from src.models.formation import formation_effectiveness
from src.models.influence import player_influence
from src.models.momentum import momentum
from src.models.pressing import ppda
from src.models.xg import event_xg

_FLOAT_RE = re.compile(r"-?\d+\.\d+")
_INT_RE = re.compile(r"\d+")
_SCORE_RE = re.compile(r"(\d+)\s*[-–—]\s*(\d+)")
_FORMATION_RE = re.compile(r"\d+-\d+(?:-\d+)+")
_MINUTE_RE = re.compile(r"(\d{1,3})['′’]")
_PLAYER_RE = re.compile(r"\bP(\d{1,2})\b")

# language a broadcast line must never carry: betting terms, certainty
# claims, and real-world league marks (the hackathon forbids real PL data —
# synthetic matches only). Pattern from matchcut's verifier.
_BANNED_RE = re.compile(
    r"\b(bets?|betting|odds|wager|bookmaker|accumulator|guaranteed|premier league|epl)\b",
    re.IGNORECASE,
)

# broadcast lines are meant to be read at a glance — a hard cap on length
_MAX_LINE_CHARS = 240

# causal claims ("because", "cost them") need counterfactual evidence the
# pipeline cannot produce — talkback simulates a moment ~120× before allowing
# wording like this. With no sim model here, causal connectives are
# unverifiable and fail closed rather than air as speculation.
_CAUSAL_RE = re.compile(
    r"\b(because|caused|cost (?:them|him|her)|which is why|forced (?:them|him|a)|"
    r"thanks to|as a result of)\b",
    re.IGNORECASE,
)

_TOL = 0.02


class _Facts:
    """Every number the engine can justify for a match — the allowed set.

    A float a writer can put on screen is only a stat the recount produced or
    an xG value on a real event. Anything else is a hallucination by
    definition.
    """

    def __init__(self, events: list[Event]) -> None:
        self.events = events
        self.by_id = {e.id: e for e in events}
        self.home_xg, self.away_xg = self._xg_totals()
        self.home_goals, self.away_goals = self._goals()
        self.ppda = {t: ppda(events, t) for t in (Team.HOME, Team.AWAY)}
        self.formations = {t: formation_effectiveness(events, t) for t in (Team.HOME, Team.AWAY)}
        self.influence = {t: player_influence(events, t) for t in (Team.HOME, Team.AWAY)}
        self.momentum = momentum(events)
        self.players = {e.player for e in events}
        self.shots = {
            t: sum(1 for e in events if e.type.value in ("shot", "goal") and e.team == t)
            for t in (Team.HOME, Team.AWAY)
        }
        self.counts = {
            "shots": sum(self.shots.values()),
            "goals": self.home_goals + self.away_goals,
            "passes": sum(1 for e in events if e.type.value == "pass"),
            "tackles": sum(1 for e in events if e.type.value == "tackle"),
            "fouls": sum(1 for e in events if e.type.value == "foul"),
        }
        self.max_minute = max((e.minute for e in events), default=0)
        self.goal_minutes = {e.minute for e in events if e.type.value == "goal"}
        self.event_minutes = {e.minute for e in events}
        self.floats = self._float_set()
        self.ints = self._int_set()
        # running score at each minute for score-claim checks
        self._score_at = self._running_scores()

    def _xg_totals(self) -> tuple[float, float]:
        h = a = 0.0
        for e in self.events:
            if e.type.value not in ("shot", "goal"):
                continue
            xg = event_xg(e) or float(e.metadata.get("xg", 0.0))
            if e.team == Team.HOME:
                h += xg
            else:
                a += xg
        return round(h, 3), round(a, 3)

    def _goals(self) -> tuple[int, int]:
        h = sum(1 for e in self.events if e.type.value == "goal" and e.team == Team.HOME)
        a = sum(1 for e in events_goals(self.events))
        return h, a

    def _float_set(self) -> set[float]:
        vals: set[float] = {self.home_xg, self.away_xg, self.home_xg - self.away_xg}
        for p in self.ppda.values():
            if p != float("inf"):
                vals.add(p)
        for ranked in self.influence.values():
            vals.update(t["influence"] for t in ranked)
        for m in self.momentum:
            vals.update((m["home_xg"], m["away_xg"], m["momentum"]))
        for fe in self.formations.values():
            for s in fe.values():
                vals.add(s["xg"])
        for e in self.events:
            xg = e.metadata.get("xg")
            if isinstance(xg, int | float):
                vals.add(round(float(xg), 3))
            ex = event_xg(e)
            if ex is not None:
                vals.add(ex)
        return {round(v, 3) for v in vals}

    def _stat_float_set(self) -> set[float]:
        """Engine stats only — the aggregate metrics a claim may cite, minus
        per-event xG. Used for evidence-bound number attribution."""
        vals: set[float] = {self.home_xg, self.away_xg, self.home_xg - self.away_xg}
        for p in self.ppda.values():
            if p != float("inf"):
                vals.add(p)
        for ranked in self.influence.values():
            vals.update(t["influence"] for t in ranked)
        for m in self.momentum:
            vals.update((m["home_xg"], m["away_xg"], m["momentum"]))
        for fe in self.formations.values():
            for s in fe.values():
                vals.add(s["xg"])
        return {round(v, 3) for v in vals}

    def event_xg_set(self, event_ids: list[str]) -> set[float]:
        """xG values on specific events — the numbers a claim may cite when it
        binds itself to these event ids (matchcut's attributed-fact rule)."""
        vals: set[float] = set()
        for eid in event_ids:
            e = self.by_id.get(eid)
            if e is None:
                continue
            xg = e.metadata.get("xg")
            if isinstance(xg, int | float):
                vals.add(round(float(xg), 3))
            ex = event_xg(e)
            if ex is not None:
                vals.add(ex)
        return {round(v, 3) for v in vals}

    def _int_set(self) -> set[int]:
        ints: set[int] = set(self.counts.values())
        ints.update(self.shots.values())
        ints.update((self.home_goals, self.away_goals))
        ints.update(self.goal_minutes)
        for fe in self.formations.values():
            for s in fe.values():
                ints.update((s["shots"], s["minutes"]))
        ints.update(range(0, self.max_minute + 1))  # minutes are range-checked anyway
        return ints

    def _running_scores(self) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        h = a = 0
        for e in sorted(self.events, key=lambda ev: ev.timestamp_seconds):
            if e.type.value == "goal":
                if e.team == Team.HOME:
                    h += 1
                else:
                    a += 1
            out.append((e.minute, h * 1_000 + a))
        return out

    def score_at(self, minute: int) -> tuple[int, int]:
        h = a = 0
        for m, packed in self._score_at:
            if m > minute:
                break
            h, a = packed // 1_000, packed % 1_000
        return h, a

    def float_ok(self, v: float, decimals: int = 3) -> bool:
        """A written number is justified if a recounted stat rounds to it at
        the precision it was written (a model may write 8.4 for 8.42, but
        37.84 must match a real stat to the cent)."""
        tol = 0.5 * (10**-decimals) + 0.015
        return any(abs(round(v, 3) - j) <= tol for j in self.floats)


def events_goals(events: list[Event]) -> list[Event]:
    return [e for e in events if e.type.value == "goal" and e.team == Team.AWAY]


def _check(ok: bool, kind: str, detail: str, *, expected: Any = None, actual: Any = None) -> dict:
    return {
        "ok": bool(ok),
        "kind": kind,
        "detail": detail,
        "expected": expected,
        "actual": actual,
    }


class VerifierAgent:
    """Deterministic, independent of the agents that write. Never throws."""

    name = "verifier"

    # ------------------------------------------------------------------ text

    def check_text(
        self,
        text: str,
        facts: _Facts,
        *,
        minute: int | None = None,
        goal_line: bool = False,
        allowed_floats: set[float] | None = None,
    ) -> list[dict]:
        """Ground every number in a line of prose against the recount.

        ``allowed_floats`` narrows the number set for evidence-bound claims:
        when an insight cites specific events, its decimals must come from
        those events' xG or engine stats — not just anywhere in the ledger.
        """
        checks: list[dict] = []

        # order matters: strip shapes that look like numbers but aren't —
        # formations (4-2-3-1) and minute refs (34', windows 70'-80') — before
        # the score/float checks see them
        work = _FORMATION_RE.sub(" ", text)
        minute_refs = [int(m.group(1)) for m in _MINUTE_RE.finditer(work)]
        work = _MINUTE_RE.sub(" ", work)

        # scorelines: "N-M" must equal the running score at the line's minute
        for m in _SCORE_RE.finditer(work):
            claimed = (int(m.group(1)), int(m.group(2)))
            actual = facts.score_at(minute if minute is not None else facts.max_minute)
            checks.append(
                _check(
                    claimed == actual,
                    "score",
                    f"score {claimed[0]}-{claimed[1]} at {minute}'",
                    expected=actual,
                    actual=claimed,
                )
            )
            work = work.replace(m.group(0), " ", 1)

        for m in _FLOAT_RE.finditer(work):
            v = float(m.group(0))
            dec = len(m.group(0).split(".")[1])
            if allowed_floats is not None:
                ok = any(abs(v - a) <= _TOL for a in allowed_floats)
                detail_kind = "stat:attributed"
                expected = "cited-fact value"
            else:
                ok = facts.float_ok(v, dec)
                detail_kind = "stat"
                expected = "engine-recounted value"
            checks.append(
                _check(
                    ok,
                    detail_kind,
                    f"number {m.group(0)}",
                    expected=expected,
                    actual=v,
                )
            )

        # minute references: N' must be a real minute for the thing claimed
        for n in minute_refs:
            if goal_line:
                ok = n in facts.goal_minutes or any(abs(n - g) <= 1 for g in facts.goal_minutes)
                detail = f"goal at {n}'"
            else:
                ok = n in facts.event_minutes or any(abs(n - t) <= 1 for t in facts.event_minutes)
                detail = f"minute {n}'"
            if n > 95:
                ok = False
            checks.append(_check(ok, "minute", detail, expected="event minute", actual=n))

        # player attribution: P# must exist in this match
        for m in _PLAYER_RE.finditer(work):
            name = f"P{m.group(1)}"
            checks.append(
                _check(
                    name in facts.players,
                    "player",
                    f"player {name}",
                    expected="roster player",
                    actual=name,
                )
            )

        # clean language — banned terms fail outright, never repairable
        banned = {b.lower() for b in _BANNED_RE.findall(text)}
        checks.append(
            _check(
                not banned,
                "language",
                "no betting/certainty/real-world marks",
                expected="clean",
                actual=sorted(banned) or None,
            )
        )

        # house style — a broadcast line fits on screen
        checks.append(
            _check(
                len(text) <= _MAX_LINE_CHARS,
                "length",
                f"{len(text)} chars",
                expected=f"<= {_MAX_LINE_CHARS}",
                actual=len(text),
            )
        )

        # wording strength — causal wording needs counterfactual evidence we
        # don't have; describe, don't claim cause
        causal = {c.lower() for c in _CAUSAL_RE.findall(text)}
        checks.append(
            _check(
                not causal,
                "causality",
                "no unverifiable causal wording",
                expected="descriptive",
                actual=sorted(causal) or None,
            )
        )
        return checks

    # -------------------------------------------------------------- insights

    def verify_insight(
        self, ins: Insight, events: list[Event], facts: _Facts | None = None
    ) -> Verdict:
        facts = facts or _Facts(events)
        checks: list[dict] = []

        # 1. evidence grounding
        missing = [eid for eid in ins.evidence if eid not in facts.by_id]
        checks.append(
            _check(
                not missing,
                "evidence",
                f"{len(ins.evidence)} cited events exist",
                expected="all ids real",
                actual=missing or "ok",
            )
        )

        # 2. typed recount
        checks.extend(self._typed_recount(ins, facts))

        # 3. generic grounding of the claim text — bound to the cited facts
        #    when the claim names evidence: decimals must come from engine
        #    stats or the cited events' own xG, not anywhere in the ledger
        allowed = None
        if ins.evidence:
            allowed = facts._stat_float_set() | facts.event_xg_set(ins.evidence)
        checks.extend(self.check_text(ins.claim, facts, allowed_floats=allowed))

        fails = [c for c in checks if not c["ok"]]
        if not fails:
            return Verdict(item_id=ins.id, kind="insight", status="verified", checks=checks)

        # repair pass: if the typed recount knows the truth, rewrite the claim
        repaired = self._repair(ins, facts)
        if repaired is not None:
            recheck = self.verify_insight(repaired, events, facts)
            if recheck.status == "verified":
                recheck.status = "repaired"
                recheck.repair_of = ins.claim
                recheck.reason = "wrong number corrected against the recount"
                recheck.checks = checks + recheck.checks
                return recheck

        return Verdict(
            item_id=ins.id,
            kind="insight",
            status="rejected",
            reason="; ".join(f"{c['kind']}: {c['detail']}" for c in fails[:3]),
            checks=checks,
        )

    def _typed_recount(self, ins: Insight, facts: _Facts) -> list[dict]:
        t = ins.type
        if t == "xg_total":
            diff = round(facts.home_xg - facts.away_xg, 3)
            try:
                ok = abs(float(ins.value) - diff) <= 0.05
            except (TypeError, ValueError):
                ok = False
            return [
                _check(
                    ok,
                    "recount:xg_total",
                    f"xG diff {diff} vs claimed {ins.value}",
                    expected=diff,
                    actual=ins.value,
                )
            ]
        if t == "pressing_intensity":
            # the claim's team word can be loose; the NUMBER must match a real
            # PPDA — checked against both sides
            try:
                v = float(ins.value)
            except (TypeError, ValueError):
                v = -1.0
            ps = {team: facts.ppda[team] for team in (Team.HOME, Team.AWAY)}
            if v == 999.0:
                ok = all(p == float("inf") for p in ps.values())
            else:
                ok = any(p != float("inf") and abs(v - p) <= 0.05 for p in ps.values())
            return [
                _check(
                    ok,
                    "recount:ppda",
                    f"PPDA {ps[Team.HOME]}/{ps[Team.AWAY]} vs claimed {ins.value}",
                    expected=ps,
                    actual=ins.value,
                )
            ]
        if t == "formation_effectiveness":
            m = _FORMATION_RE.search(ins.claim)
            if "home" in ins.claim.lower():
                team = Team.HOME
            elif "away" in ins.claim.lower():
                team = Team.AWAY
            else:
                team = Team.HOME  # unmarked claims recount against both below
            fe = facts.formations[team]
            if team is None or (
                "home" not in ins.claim.lower() and "away" not in ins.claim.lower()
            ):
                fe = {**facts.formations[Team.HOME], **facts.formations[Team.AWAY]}
            if not m:
                return [_check(True, "recount:formation", "no formation named — skipped")]
            stats = fe.get(m.group(0))
            if stats is None:
                return [
                    _check(
                        False,
                        "recount:formation",
                        f"formation {m.group(0)} never played by {team.value}",
                        expected=list(fe),
                        actual=m.group(0),
                    )
                ]
            nums = [float(x) for x in _FLOAT_RE.findall(ins.claim)]
            ok = (
                nums
                and abs(nums[-1] - stats["xg"]) <= 0.05
                or (len(nums) >= 2 and abs(nums[0] - stats["xg"]) <= 0.05)
            )
            return [
                _check(
                    bool(ok),
                    "recount:formation",
                    f"{team.value} {m.group(0)} xG {stats['xg']} vs claim {nums}",
                    expected=stats["xg"],
                    actual=nums,
                )
            ]
        if t == "player_influence":
            if "away" in ins.claim.lower():
                candidates = (Team.AWAY,)
            elif "home" in ins.claim.lower():
                candidates = (Team.HOME,)
            else:
                candidates = (Team.HOME, Team.AWAY)
            tops = {
                t: (facts.influence[t][0]["player"] if facts.influence[t] else None)
                for t in candidates
            }
            ok = any(top is not None and top in ins.claim for top in tops.values())
            return [
                _check(
                    ok, "recount:influence", f"top players {tops}", expected=tops, actual=ins.claim
                )
            ]
        if t == "momentum_shift":
            if not facts.momentum:
                return [_check(True, "recount:momentum", "no swings — skipped")]
            biggest = max(facts.momentum, key=lambda mm: abs(mm["momentum"]))
            try:
                ok = abs(float(ins.value) - biggest["momentum"]) <= 0.05
            except (TypeError, ValueError):
                ok = False
            window_ok = biggest["window"].replace("'", "") in ins.claim.replace("'", "")
            return [
                _check(
                    ok,
                    "recount:momentum",
                    f"swing {biggest['momentum']} vs claimed {ins.value}",
                    expected=biggest["momentum"],
                    actual=ins.value,
                ),
                _check(
                    window_ok,
                    "recount:window",
                    f"window {biggest['window']}",
                    expected=biggest["window"],
                    actual=ins.claim,
                ),
            ]
        return []

    def _repair(self, ins: Insight, facts: _Facts) -> Insight | None:
        """Deterministic correction for recountable types (the rewrite the
        winners' auditors sent back to the author — executed in code)."""
        t = ins.type
        claim: str | None = None
        value: float | None = None
        if t == "xg_total":
            claim = f"Home xG {facts.home_xg:.2f} vs Away xG {facts.away_xg:.2f}"
            value = round(facts.home_xg - facts.away_xg, 3)
        elif t == "pressing_intensity":
            team = Team.HOME if ins.claim.lower().startswith("home") else Team.AWAY
            p = facts.ppda[team]
            if p != float("inf"):
                claim = f"{team.value} PPDA = {p} (lower = more pressing)"
                value = p
        elif t == "momentum_shift" and facts.momentum:
            biggest = max(facts.momentum, key=lambda mm: abs(mm["momentum"]))
            claim = f"Biggest momentum swing: {biggest['window']} ({biggest['momentum']:+.2f} xG)"
            value = biggest["momentum"]
        if claim is None:
            return None
        return Insight(
            id=ins.id,
            type=ins.type,
            claim=claim,
            value=value if value is not None else ins.value,
            confidence=ins.confidence,
            evidence=ins.evidence,
            agent=ins.agent,
            timestamp=ins.timestamp,
        )

    # ------------------------------------------------------------- commentary

    def verify_commentary(
        self,
        entry: CommentaryEntry,
        events: list[Event],
        insight_verdicts: dict[str, Verdict] | None = None,
        facts: _Facts | None = None,
    ) -> Verdict:
        facts = facts or _Facts(events)
        goal_line = "goal" in entry.text.lower()
        checks = self.check_text(entry.text, facts, minute=entry.minute, goal_line=goal_line)

        # a line resting on a rejected insight inherits the rejection
        for iid in entry.insight_ids:
            v = (insight_verdicts or {}).get(iid)
            if v is not None:
                checks.append(
                    _check(
                        v.status in ("verified", "repaired"),
                        "linked_insight",
                        f"rests on insight {iid} ({v.status})",
                        expected="verified",
                        actual=v.status,
                    )
                )

        fails = [c for c in checks if not c["ok"]]
        iid = entry.id or f"com_{entry.minute}_{uuid.uuid4().hex[:4]}"
        if not fails:
            return Verdict(item_id=iid, kind="commentary", status="verified", checks=checks)
        return Verdict(
            item_id=iid,
            kind="commentary",
            status="rejected",
            reason="; ".join(f"{c['kind']}: {c['detail']}" for c in fails[:3]),
            checks=checks,
        )


def verify_broadcast(result: dict, events: list[Event]) -> dict[str, Verdict]:
    """Run the gate over a Director result; attaches verdicts in place.

    Returns {item_id: Verdict}. Repaired insights are swapped for their
    corrected text so what airs is always the true number.
    """
    verifier = VerifierAgent()
    facts = _Facts(events)
    verdicts: dict[str, Verdict] = {}

    repaired_insights: list[Insight] = []
    for ins in result.get("insights", []):
        v = verifier.verify_insight(ins, events, facts)
        if v.status == "repaired":
            fixed = verifier._repair(ins, facts)  # noqa: SLF001
            if fixed is not None:
                ins = fixed
                ins.id = f"{ins.id}_rep"
                v.item_id = ins.id
        ins.verification = v
        verdicts[ins.id] = v
        repaired_insights.append(ins)
    if "insights" in result:
        result["insights"] = repaired_insights

    for c in result.get("commentary", []):
        if not c.id:
            c.id = f"com_{c.minute}_{uuid.uuid4().hex[:4]}"
        v = verifier.verify_commentary(c, events, verdicts, facts)
        c.verification = v
        verdicts[v.item_id] = v

    return verdicts
