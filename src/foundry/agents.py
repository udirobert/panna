"""Foundry-backed agent with traced generation and deterministic fallback.

The agent's *reasoning* is the Foundry deployment (GPT-5.4 via Model Router);
the *fallback* is a deterministic local generator so the pipeline — and the
demo — never depend on the network. Every call (Foundry or fallback) is traced
(see src/foundry/tracing.py), which is what the governance panel shows.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from src.foundry.client import get_client
from src.foundry.tracing import record_span


class FoundryAgent(ABC):
    name: str = "foundry-agent"
    match_id: str = "match_001"

    @abstractmethod
    def _system_prompt(self) -> str: ...

    @abstractmethod
    def _user_payload(self, context: dict) -> str: ...

    @abstractmethod
    def _fallback(self, context: dict) -> Any:
        """Deterministic generation used when Foundry is unavailable/fails."""

    def _parse(self, raw: str, context: dict) -> Any:
        """Convert raw model text into the agent's output type. Default: raw."""
        return raw

    def generate(self, context: dict, operation: str | None = None) -> dict[str, Any]:
        op = operation or f"{self.name}.generate"
        client = get_client()
        result: Any = None
        source = "template"
        model: str | None = None
        tokens_in = tokens_out = None
        error: str | None = None
        used_foundry = False
        started = time.perf_counter()

        if client.available:
            model = client.deployment
            out = client.chat(self._system_prompt(), self._user_payload(context))
            if out is not None:
                text, tokens_in, tokens_out = out
                try:
                    parsed = self._parse(text, context)
                except Exception:  # noqa: BLE001
                    parsed = None
                if parsed is not None:
                    result, source, used_foundry = parsed, "foundry", True
                else:
                    error = "foundry reply unparseable"
            else:
                error = "foundry request failed"

        if result is None:
            source = "template"
            try:
                result = self._fallback(context)
            except Exception as exc:  # noqa: BLE001
                error = f"fallback failed: {exc}"
                result = self._fallback_safe(context)

        if used_foundry:
            status = "ok"
        elif result is None:
            status = "error"
        else:
            status = "fallback"

        record_span(
            match_id=self.match_id,
            agent=self.name,
            operation=op,
            source=source,
            model=model,
            status=status,
            duration_ms=(time.perf_counter() - started) * 1000,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            error=error,
        )
        return {"result": result, "source": source, "status": status, "model": model}

    def _fallback_safe(self, context: dict) -> Any:
        return None
