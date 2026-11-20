"""Audit ledger — the persistent record of what the gate did and who overrode it.

The winners' audit trails were durable artifacts, not process memory: a judge
(or a producer, weeks later) can answer "what aired, what was held, who approved
it?" without trusting the live session. ``MatchSession`` records four entry
types:

- ``session_start`` — match id + pipeline health when the session was built
- ``verdict``       — every line the Verifier judged (status, reason, checks)
- ``aired`` / ``suppressed`` — each gated line's air outcome per playback
- ``decision``      — every human approve/kill from the producer console

Format is JSONL (one entry per line, append-only) so the ledger survives a
crash mid-write with at most one torn tail line. File-backed by default;
``PANNA_AUDIT_PATH`` points it anywhere (a mounted volume on ACA). Set
``PANNA_AUDIT=off`` to disable. Writing is fail-soft by contract — an audit
failure must never take the broadcast down.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Protocol

DEFAULT_AUDIT_PATH = Path(__file__).resolve().parent.parent / "reports" / "audit.jsonl"


class AuditLedger(Protocol):
    def record(self, entry: dict[str, Any]) -> None: ...


class NullLedger:
    def record(self, entry: dict[str, Any]) -> None:  # noqa: ARG002
        return


class JsonlLedger:
    """Append-only JSONL ledger. Open-per-write keeps the tail durable."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, entry: dict[str, Any]) -> None:
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": round(time.time(), 3), **entry}) + "\n")
        except OSError as exc:  # audit must never break broadcast
            print(f"[audit] ledger write failed: {exc}", file=sys.stderr)


def load_audit_ledger(env: dict[str, str] | None = None) -> AuditLedger:
    """Ledger from env: PANNA_AUDIT=off disables; PANNA_AUDIT_PATH relocates."""
    env = env if env is not None else os.environ
    if env.get("PANNA_AUDIT", "").lower() == "off":
        return NullLedger()
    path = Path(env.get("PANNA_AUDIT_PATH") or DEFAULT_AUDIT_PATH)
    try:
        return JsonlLedger(path)
    except OSError as exc:
        print(f"[audit] ledger unavailable at {path}: {exc}", file=sys.stderr)
        return NullLedger()
