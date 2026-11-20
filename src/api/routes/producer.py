"""Producer console API: the human gate the winners all shipped.

- ``GET  /producer/{match_id}/board``   — every broadcast line, its verdict,
  and its air status (aired | queued | held | killed).
- ``POST /producer/{match_id}/decide``  — approve a held line (it airs on the
  next beat) or kill it outright.

The board is the audit trail a judge can act on: a rejected line sits in
``held`` with the failed checks attached until a human clears or kills it.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.api.session import get_session

router = APIRouter()


class Decision(BaseModel):
    item_id: str = Field(..., description="id of the insight/commentary to rule on")
    decision: str = Field(..., description="approve | kill")


@router.get("/{match_id}/board")
def board(match_id: str) -> dict:
    session = get_session(match_id)
    if session is None:
        raise HTTPException(404, "no active session; open /stream/{match_id} first")
    rows = session.board()
    return {
        "match_id": match_id,
        "clock": int(session.clock),
        "verification": session.result.get("verification", {}),
        "items": rows,
    }


@router.post("/{match_id}/decide")
def decide(match_id: str, cmd: Decision) -> dict:
    session = get_session(match_id)
    if session is None:
        raise HTTPException(404, "no active session; open /stream/{match_id} first")
    try:
        result = session.decide(cmd.item_id, cmd.decision)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"match_id": match_id, **result}
