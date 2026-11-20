"""Speech endpoint — voices a verified line through Azure AI Speech.

POST {text, voice?} → audio/mpeg. When Speech isn't configured the endpoint
answers 503 with the honest staged status — the client falls back to the
text AD feed, which is always on. Callers are expected to send only
post-Verifier text (speech is a render step, never a trust step).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from src.foundry.speech import get_speech

router = APIRouter()


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    voice: str | None = None


@router.post("/speak")
def speak(req: SpeakRequest) -> Response:
    speech = get_speech()
    if not speech.available:
        raise HTTPException(
            status_code=503,
            detail={
                "speech": "unconfigured",
                "staged": "set SPEECH_KEY+SPEECH_REGION (or SPEECH_AUTH=entra) "
                "for spoken audio; the text AD feed is always on",
                "auth_mode": speech.auth_mode,
            },
        )
    audio = speech.synthesize(req.text, voice=req.voice)
    if audio is None:
        raise HTTPException(status_code=502, detail="speech synthesis failed upstream")
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"X-Panna-Voice": req.voice or speech.voice},
    )


@router.get("/capability")
def capability() -> dict:
    """Honest capability probe — the frontend can grey the audio toggle."""
    speech = get_speech()
    return {
        "available": speech.available,
        "auth_mode": speech.auth_mode,
        "voice": speech.voice,
        "chars_sent": speech.chars_sent,
    }
