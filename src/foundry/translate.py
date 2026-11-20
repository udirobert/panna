"""Azure AI Translator client — lazy, batched, fail-soft.

Localizes verified lines into the demo language set. Translation is a
*rendering* step on canonical text that has already passed the Verifier: the
gate counts numbers in the ledger, the translator only re-phrases them, so
the invariant "nothing unverified airs" holds in every language.

Auth follows the same pattern as the Foundry client: ``TRANSLATOR_KEY`` for
local development, or ``TRANSLATOR_AUTH=entra`` + ``TRANSLATOR_REGION`` for
keyless managed-identity on Azure (Bearer token + region header). When
nothing is configured the client reports itself unavailable and callers fall
back to the original text — honestly labelled, never silently.

Cost is honest too: ``chars_sent`` counts billable characters actually sent,
which is how Translator is metered.
"""

from __future__ import annotations

import os

import httpx

API_VERSION = "3.0"
_GLOBAL_ENDPOINT = "https://api.cognitive.microsofttranslator.com"

# demo language set (all real when the client is configured)
LANGUAGES = ("en", "es", "fr", "pt", "de")
AUDIENCES = ("fan", "analyst", "kids", "ad")


class TranslatorClient:
    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self.endpoint = os.getenv("TRANSLATOR_ENDPOINT", _GLOBAL_ENDPOINT).rstrip("/")
        self.region = os.getenv("TRANSLATOR_REGION", "")
        self.api_key = os.getenv("TRANSLATOR_KEY", "")
        self.auth_mode = "none"  # none | api-key | entra
        self.chars_sent = 0
        self._token_provider = None
        self._http = httpx.Client(transport=transport, timeout=10.0)
        if self.api_key:
            self.auth_mode = "api-key"
        elif os.getenv("TRANSLATOR_AUTH") == "entra" and self.region:
            try:
                from azure.identity import DefaultAzureCredential, get_bearer_token_provider

                self._token_provider = get_bearer_token_provider(
                    DefaultAzureCredential(),
                    "https://cognitiveservices.azure.com/.default",
                )
                self.auth_mode = "entra"
            except Exception:  # noqa: BLE001
                self._token_provider = None

    @property
    def available(self) -> bool:
        return self.auth_mode != "none"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.auth_mode == "api-key":
            headers["Ocp-Apim-Subscription-Key"] = self.api_key
            if self.region:
                headers["Ocp-Apim-Subscription-Region"] = self.region
        elif self.auth_mode == "entra" and self._token_provider is not None:
            headers["Authorization"] = f"Bearer {self._token_provider()}"
            headers["Ocp-Apim-Subscription-Region"] = self.region
        return headers

    def translate(self, texts: list[str], to: str) -> list[str] | None:
        """Translate a batch. Returns None on any failure — caller falls back."""
        if not self.available or to == "en" or not texts:
            return None
        try:
            resp = self._http.post(
                f"{self.endpoint}/translate",
                params={"api-version": API_VERSION, "to": to},
                headers=self._headers(),
                json=[{"Text": t} for t in texts],
            )
            resp.raise_for_status()
            body = resp.json()
            out = [item["translations"][0]["text"] for item in body]
            self.chars_sent += sum(len(t) for t in texts)
            return out
        except Exception:  # noqa: BLE001
            return None


_client: TranslatorClient | None = None


def get_translator() -> TranslatorClient:
    global _client
    if _client is None:
        _client = TranslatorClient()
    return _client
