"""Draft Simulator Router."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Body
from pydantic import BaseModel, Field
from app.services.draft import (
    advance_next_game,
    create_draft_session,
    execute_action,
    get_draft_state,
    get_series_history,
)
from app.services.recommend import get_recommendations

router = APIRouter()


class CreateDraftRequest(BaseModel):
    blue_team_id: str = Field(..., example="t01")
    red_team_id: str = Field(..., example="t02")
    series_type: str = Field("BO3", example="BO3")


class DraftActionRequest(BaseModel):
    champion_id: str = Field(..., example="c001")
    side: str = Field(..., example="blue")


class NextGameRequest(BaseModel):
    winner: Optional[str] = Field(None, example="blue")


@router.post("/draft")
def api_create_draft(payload: CreateDraftRequest):
    return create_draft_session(
        blue_team_id=payload.blue_team_id,
        red_team_id=payload.red_team_id,
        series_type=payload.series_type,
    )


@router.get("/draft/{draft_id}")
def api_get_draft(draft_id: str):
    return get_draft_state(draft_id)


@router.post("/draft/{draft_id}/ban")
def api_ban(draft_id: str, payload: DraftActionRequest):
    return execute_action(
        draft_id=draft_id,
        side=payload.side,
        action="ban",
        champion_id=payload.champion_id,
    )


@router.post("/draft/{draft_id}/pick")
def api_pick(draft_id: str, payload: DraftActionRequest):
    return execute_action(
        draft_id=draft_id,
        side=payload.side,
        action="pick",
        champion_id=payload.champion_id,
    )


@router.post("/draft/{draft_id}/recommend")
def api_recommend(draft_id: str):
    return get_recommendations(draft_id)


@router.post("/draft/{draft_id}/next-game")
def api_next_game(draft_id: str, payload: Optional[NextGameRequest] = Body(default=None)):
    winner = payload.winner if payload else None
    return advance_next_game(draft_id, winner=winner)


@router.get("/draft/{draft_id}/history")
def api_history(draft_id: str):
    return get_series_history(draft_id)
