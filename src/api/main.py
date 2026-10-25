"""FastAPI service for Panna match intelligence."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import agentic, commentary, events, insights, matches, recap, share, stream
from src.foundry.client import get_client

app = FastAPI(title="Panna", version="0.1.0", description="AI-driven match intelligence")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(matches.router, prefix="/matches", tags=["matches"])
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(insights.router, prefix="/insights", tags=["insights"])
app.include_router(commentary.router, prefix="/commentary", tags=["commentary"])
app.include_router(recap.router, prefix="/recap", tags=["recap"])
app.include_router(stream.router, prefix="/stream", tags=["stream"])
app.include_router(agentic.router, prefix="/agentic", tags=["agentic"])
app.include_router(share.router, prefix="/share", tags=["share"])


@app.get("/health")
def health() -> dict:
    client = get_client()
    return {
        "status": "ok",
        "service": "panna",
        "foundry": {
            "available": client.available,
            "deployment": client.deployment,
        },
    }
