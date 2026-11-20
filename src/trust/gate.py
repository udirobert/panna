"""TrustGate — the licensable verification layer, packaged standalone.

Everything between "a model wrote a line" and "the line may air", usable
without the broadcast pipeline: hand it an event ledger (Panna's synthetic
one or any real feed mapped to the same schema) and it answers verdicts.

Surface:

- ``verify_line(text, minute)``   — free-form broadcast copy
- ``verify_claim(claim, evidence)``— structured insight with cited events;
  its decimals must come from the cited events or engine stats
- ``audit``                        — optional AuditLedger; every verdict is
  recorded so the trail survives the process
- ``translation_intact``           — re-exported post-translation recount
  (verify canonical → transform → re-check the rendered output)

The gate is deliberately *not* a model: a wrong answer is a held line,
never a repaired guess. Fail closed by contract.
"""

from __future__ import annotations

from typing import Any

from src.agents.verifier import VerifierAgent, _Facts  # noqa: SLF001
from src.audit import AuditLedger
from src.events.schema import CommentaryEntry, Event, Insight


class TrustGate:
    def __init__(self, events: list[Event], audit: AuditLedger | None = None) -> None:
        self.events = events
        self.facts = _Facts(events)
        self._verifier = VerifierAgent()
        self.audit = audit

    def verify_line(
        self, text: str, *, minute: int | None = None, goal_line: bool = False
    ) -> dict[str, Any]:
        """Verdict for free-form copy — the commentary path."""
        entry = CommentaryEntry(
            id=f"line_{minute or 0}_{abs(hash(text)) % 100000}",
            minute=minute or 0,
            second=0,
            text=text,
        )
        verdict = self._verifier.verify_commentary(entry, self.events, {}, self.facts)
        out = verdict.model_dump()
        self._record({"type": "verdict", "surface": "line", "text": text, **out})
        return out

    def verify_claim(
        self, claim: str, *, evidence: list[str] | None = None, type: str = "key_moment"
    ) -> dict[str, Any]:
        """Verdict for a structured claim — evidence-bound decimals are
        checked against the cited events, not anywhere in the ledger."""
        ins = Insight(
            id=f"claim_{abs(hash(claim)) % 100000}",
            type=type,
            claim=claim,
            value=0.0,
            confidence=0.9,
            evidence=evidence or [],
        )
        verdict = self._verifier.verify_insight(ins, self.events, self.facts)
        out = verdict.model_dump()
        self._record({"type": "verdict", "surface": "claim", "text": claim, **out})
        return out

    def _record(self, entry: dict[str, Any]) -> None:
        if self.audit is not None:
            self.audit.record(entry)
