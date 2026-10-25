"""FastAPI service for Panna match intelligence."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import commentary, events, insights, matches, recap

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


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "panna"}
