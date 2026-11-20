"""Azure AI Speech client — text-to-speech for the AD/commentary tracks.

Spoken-word audio is the last staged capability: the deterministic text AD
feed is already live, and this client voices it (or any verified line) via
Azure TTS REST. Same contract as Translator — fail-soft, honestly labelled:

- ``SPEECH_KEY`` + ``SPEECH_REGION`` for local development
- ``SPEECH_AUTH=entra`` + ``SPEECH_REGION`` for keyless managed identity on
  Azure (Bearer token, same cognitiveservices scope as Translator)
- ``SPEECH_VOICE`` overrides the default voice (``en-GB-RyanNeural``)

Unconfigured → ``available`` is False → callers return the honest staged
status, never a synthesized fake. ``chars_sent`` counts billable characters.
Only *already-verified* text should reach this client — speech, like
translation, is a rendering step downstream of the gate.
"""

from __future__ import annotations

import os
from xml.sax.saxutils import escape

import httpx

DEFAULT_VOICE = "en-GB-RyanNeural"
_OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3"


class SpeechClient:
    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self.region = os.getenv("SPEECH_REGION", "")
        self.endpoint = os.getenv(
            "SPEECH_ENDPOINT",
            f"https://{self.region}.tts.speech.microsoft.com" if self.region else "",
        ).rstrip("/")
        self.api_key = os.getenv("SPEECH_KEY", "")
        self.voice = os.getenv("SPEECH_VOICE", DEFAULT_VOICE)
        self.auth_mode = "none"  # none | api-key | entra
        self.chars_sent = 0
        self._token_provider = None
        self._http = httpx.Client(transport=transport, timeout=15.0)
        if self.api_key and self.region:
            self.auth_mode = "api-key"
        elif os.getenv("SPEECH_AUTH") == "entra" and self.region:
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
        return self.auth_mode != "none" and bool(self.endpoint)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": _OUTPUT_FORMAT,
            "User-Agent": "panna",
        }
        if self.auth_mode == "api-key":
            headers["Ocp-Apim-Subscription-Key"] = self.api_key
        elif self.auth_mode == "entra" and self._token_provider is not None:
            headers["Authorization"] = f"Bearer {self._token_provider()}"
        return headers

    def synthesize(self, text: str, *, voice: str | None = None) -> bytes | None:
        """Synthesize one line to MP3 bytes. None on any failure — caller
        reports the honest staged status rather than serving silence."""
        if not self.available or not text:
            return None
        voice = voice or self.voice
        lang = voice[:5] if len(voice) >= 5 else "en-GB"
        ssml = (
            '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            f'xml:lang="{lang}"><voice name="{escape(voice)}">'
            f"{escape(text)}</voice></speak>"
        )
        try:
            resp = self._http.post(
                f"{self.endpoint}/cognitiveservices/v1",
                headers=self._headers(),
                content=ssml,
            )
            resp.raise_for_status()
            self.chars_sent += len(text)
            return resp.content
        except Exception:  # noqa: BLE001
            return None


_client: SpeechClient | None = None


def get_speech() -> SpeechClient:
    global _client
    if _client is None:
        _client = SpeechClient()
    return _client
