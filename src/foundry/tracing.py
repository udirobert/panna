"""Lightweight agent tracing.

Every pipeline step (LLM-backed or template fallback) emits a span. Spans are
kept per match in a bounded ring buffer and exposed at ``GET /tracing`` so the
governance story (tracing for all agents) is observable, not asserted.
"""

from __future__ import annotations

import itertools
import time
from dataclasses import asdict, dataclass, field


@dataclass
class Span:
    id: str
    match_id: str
    agent: str
    operation: str
    source: str = "template"  # foundry | template
    model: str | None = None
    status: str = "ok"  # ok | fallback | error
    duration_ms: float = 0.0
    tokens_in: int | None = None
    tokens_out: int | None = None
    ts: float = field(default_factory=time.time)
    error: str | None = None


_TRACES: dict[str, list[Span]] = {}
_RING = 200
_IDS = itertools.count(1)


def record_span(
    *,
    match_id: str,
    agent: str,
    operation: str,
    source: str = "template",
    model: str | None = None,
    status: str = "ok",
    duration_ms: float = 0.0,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    error: str | None = None,
) -> Span:
    span = Span(
        id=f"span_{next(_IDS):05d}",
        match_id=match_id,
        agent=agent,
        operation=operation,
        source=source,
        model=model,
        status=status,
        duration_ms=round(duration_ms, 1),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        error=error,
    )
    _TRACES.setdefault(match_id, []).append(span)
    if len(_TRACES[match_id]) > _RING:
        _TRACES[match_id] = _TRACES[match_id][-_RING:]
    return span


def spans_for(match_id: str) -> list[Span]:
    return _TRACES.get(match_id, [])


def summary_for(match_id: str) -> dict:
    spans = _TRACES.get(match_id, [])
    return {
        "match_id": match_id,
        "span_count": len(spans),
        "foundry_calls": sum(1 for s in spans if s.source == "foundry"),
        "fallback_calls": sum(1 for s in spans if s.source == "template"),
        "errors": sum(1 for s in spans if s.status == "error"),
        "total_tokens": sum((s.tokens_in or 0) + (s.tokens_out or 0) for s in spans),
    }


def to_dicts(match_id: str) -> list[dict]:
    return [asdict(s) for s in _TRACES.get(match_id, [])]


def reset(match_id: str) -> None:
    _TRACES.pop(match_id, None)
