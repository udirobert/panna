"""Synthetic football event schema (StatsBomb-like)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Team(StrEnum):
    HOME = "Home"
    AWAY = "Away"


class Position(BaseModel):
    x: float = Field(..., ge=0, le=120, description="Pitch x (0-120)")
    y: float = Field(..., ge=0, le=80, description="Pitch y (0-80)")


class EventType(StrEnum):
    PASS = "pass"  # noqa: S105
    SHOT = "shot"
    TACKLE = "tackle"
    INTERCEPTION = "interception"
    FOUL = "foul"
    POSSESSION_CHANGE = "possession_change"
    FORMATION_CHANGE = "formation_change"
    SUBSTITUTION = "substitution"
    SET_PIECE = "set_piece"
    GOAL = "goal"
    CARRY = "carry"
    PRESSURE = "pressure"


class Event(BaseModel):
    """A single synthetic match event."""

    id: str = Field(..., description="Unique event id, e.g. evt_0042")
    match_id: str
    minute: int = Field(..., ge=0, le=120)
    second: int = Field(..., ge=0, le=59)
    type: EventType
    player: str
    team: Team
    position: Position
    end_location: Position | None = None
    outcome: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def timestamp_seconds(self) -> int:
        return self.minute * 60 + self.second


class Insight(BaseModel):
    """Explainable tactical insight produced by the Analyst agent."""

    id: str
    type: str
    claim: str
    value: float | str
    confidence: float = Field(..., ge=0, le=1)
    evidence: list[str] = Field(..., description="List of event ids supporting this insight")
    agent: str = "analyst"
    timestamp: str = "0:00"


class KeyMoment(BaseModel):
    """Key moment flagged by the Scout agent."""

    id: str
    event_id: str
    minute: int
    type: str
    importance: float = Field(..., ge=0, le=1)
    description: str
    evidence: list[str] = Field(default_factory=list)


class CommentaryEntry(BaseModel):
    """Timed broadcast commentary produced by the Commentator agent."""

    minute: int
    second: int
    text: str
    tone: str = "broadcast"
    insight_ids: list[str] = Field(default_factory=list)


class AgentHealth(BaseModel):
    agent: str
    status: str = "healthy"  # healthy | degraded | down
    last_ok: str | None = None
    error: str | None = None
