"""Base agent interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    def run(self, context: dict[str, Any]) -> Any: ...

    def safe_run(self, context: dict[str, Any]) -> tuple[Any, str | None]:
        """Run with failure capture. Returns (result, error)."""
        try:
            return self.run(context), None
        except Exception as exc:  # noqa: BLE001
            return None, f"{type(exc).__name__}: {exc}"
