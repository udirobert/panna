"""Microsoft Foundry client (Azure OpenAI via Foundry).

Uses the OpenAI SDK against an Azure OpenAI / Foundry endpoint. Falls back to a
deterministic stub when credentials are not configured, so the pipeline always runs.
"""

from __future__ import annotations

import os
from typing import Any


class FoundryClient:
    def __init__(self) -> None:
        self.endpoint = os.getenv("FOUNDRY_ENDPOINT", "")
        self.deployment = os.getenv("FOUNDRY_DEPLOYMENT", "gpt-5.4")
        self.api_key = os.getenv("FOUNDRY_API_KEY", "")
        self._client = None
        if self.endpoint and self.api_key:
            try:
                from openai import AzureOpenAI

                self._client = AzureOpenAI(
                    azure_endpoint=self.endpoint,
                    api_key=self.api_key,
                    api_version=os.getenv("FOUNDRY_API_VERSION", "2024-10-21"),
                )
            except Exception:  # noqa: BLE001
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def chat(self, system: str, user: str, **kwargs: Any) -> str:
        if self._client is None:
            return f"[foundry-stub] {user[:120]}"
        try:
            resp = self._client.chat.completions.create(
                model=self.deployment,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=kwargs.get("temperature", 0.4),
                max_tokens=kwargs.get("max_tokens", 400),
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001
            return f"[foundry-error] {exc}"


def get_client() -> FoundryClient:
    return FoundryClient()
