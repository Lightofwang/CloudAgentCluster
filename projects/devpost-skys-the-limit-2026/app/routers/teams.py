"""Teams, Players, Matches, and Champions endpoints."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.db import get_connection, row_to_dict

router = APIRouter()


@router.get("/teams")
def list_teams(style: Optional[str] = Query(None, description="Filter by team style")):
    conn = get_connection()
    try:
        cur = conn.cursor()
        if style:
            cur.execute("SELECT * FROM teams WHERE style = ?", (style,))
        else:
            cur.execute("SELECT * FROM teams ORDER BY win_rate DESC")
        rows = cur.fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/teams/{team_id}")
def get_team(team_id: str):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM teams WHERE id = ?", (team_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")
        team = row_to_dict(row)

        # Also attach roster players and recent 5 matches
        cur.execute("SELECT * FROM players WHERE team_id = ? ORDER BY id ASC", (team_id,))
        team["players"] = [row_to_dict(p) for p in cur.fetchall()]

        cur.execute(
            "SELECT * FROM matches WHERE team_id = ? OR opponent_id = ? ORDER BY played_at DESC LIMIT 5",
            (team_id, team_id),
        )
        team["recent_matches"] = [row_to_dict(m) for m in cur.fetchall()]
        return team
    finally:
        conn.close()


@router.get("/players")
def list_players(team_id: Optional[str] = Query(None, description="Filter by team ID")):
    conn = get_connection()
    try:
        cur = conn.cursor()
        if team_id:
            cur.execute("SELECT * FROM players WHERE team_id = ? ORDER BY id ASC", (team_id,))
        else:
            cur.execute("SELECT * FROM players ORDER BY team_id, id ASC")
        rows = cur.fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/matches")
def list_matches(
    team_id: Optional[str] = Query(None, description="Filter by team ID"),
    limit: int = Query(20, ge=1, le=100, description="Page limit, default 20, max 100"),
):
    conn = get_connection()
    try:
        cur = conn.cursor()
        if team_id:
            cur.execute(
                "SELECT * FROM matches WHERE team_id = ? OR opponent_id = ? ORDER BY played_at DESC LIMIT ?",
                (team_id, team_id, limit),
            )
        else:
            cur.execute("SELECT * FROM matches ORDER BY played_at DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/champions")
def list_champions(role: Optional[str] = Query(None, description="Filter by role")):
    conn = get_connection()
    try:
        cur = conn.cursor()
        if role:
            cur.execute("SELECT * FROM champions WHERE role = ? ORDER BY win_rate DESC", (role.upper(),))
        else:
            cur.execute("SELECT * FROM champions ORDER BY role, win_rate DESC")
        rows = cur.fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()
