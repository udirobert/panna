"""Foundry Memory integration — stub (user/session/personalization)."""

from __future__ import annotations


class MemoryStore:
    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    def get(self, user_id: str) -> dict:
        return self._store.get(user_id, {})

    def set(self, user_id: str, prefs: dict) -> None:
        self._store[user_id] = prefs
