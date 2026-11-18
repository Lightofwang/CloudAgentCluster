"""Macro Scouting Router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from app.services.scout import generate_scout_report

router = APIRouter()


@router.get("/scout/{team_id}")
def get_scout_report(
    team_id: str,
    matches: int = Query(5, ge=1, le=50, description="Number of recent matches to analyze"),
):
    report = generate_scout_report(team_id, matches_requested=matches)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")
    return report
