"""Microsoft Foundry client (Azure OpenAI via Foundry).

Uses the OpenAI SDK against an Azure OpenAI / Foundry endpoint. Falls back to a
deterministic stub when credentials are not configured, so the pipeline always
runs. ``chat_structured`` requests JSON and returns parsed output for the
agentic narrative pass.
"""

from __future__ import annotations

import json
import os
from typing import Any


class FoundryClient:
    def __init__(self) -> None:
        self.endpoint = os.getenv("FOUNDRY_ENDPOINT", "")
        self.deployment = os.getenv("FOUNDRY_DEPLOYMENT", "gpt-5.4")
        self.api_key = os.getenv("FOUNDRY_API_KEY", "")
        self.api_version = os.getenv("FOUNDRY_API_VERSION", "2025-03-01-preview")
        self._client = None
        if self.endpoint and self.api_key:
            try:
                from openai import AzureOpenAI

                self._client = AzureOpenAI(
                    azure_endpoint=self.endpoint,
                    api_key=self.api_key,
                    api_version=self.api_version,
                )
            except Exception:  # noqa: BLE001
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def chat(self, system: str, user: str, **kwargs: Any) -> tuple[str, int, int] | None:
        """Returns (text, tokens_in, tokens_out) or None when unavailable."""
        if self._client is None:
            return None
        try:
            resp = self._client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=kwargs.get("temperature", 0.5),
                max_tokens=kwargs.get("max_tokens", 900),
            )
            text = resp.choices[0].message.content or ""
            usage = getattr(resp, "usage", None)
            tin = getattr(usage, "prompt_tokens", None) if usage else None
            tout = getattr(usage, "completion_tokens", None) if usage else None
            return text, tin or 0, tout or 0
        except Exception:  # noqa: BLE001
            return None

    def chat_structured(self, system: str, user: str, **kwargs: Any) -> Any:
        """Like chat but forces a JSON reply and parses it; None on any failure."""
        result = self.chat(
            system + "\n\nRespond ONLY with valid JSON — no prose, no markdown fences.",
            user,
            **kwargs,
        )
        if result is None:
            return None
        text = result[0].strip()
        # tolerate accidental fences
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None


_client: FoundryClient | None = None


def get_client() -> FoundryClient:
    global _client
    if _client is None:
        _client = FoundryClient()
    return _client
