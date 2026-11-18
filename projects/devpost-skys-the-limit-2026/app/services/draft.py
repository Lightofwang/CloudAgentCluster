"""Fearless Draft State Machine and Management Service."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException
from app.db import get_connection, row_to_dict

DRAFT_TURNS = [
    {"index": 0, "side": "blue", "action": "ban", "label": "蓝方 1 Ban"},
    {"index": 1, "side": "red", "action": "ban", "label": "红方 1 Ban"},
    {"index": 2, "side": "blue", "action": "ban", "label": "蓝方 2 Ban"},
    {"index": 3, "side": "red", "action": "ban", "label": "红方 2 Ban"},
    {"index": 4, "side": "blue", "action": "ban", "label": "蓝方 3 Ban"},
    {"index": 5, "side": "red", "action": "ban", "label": "红方 3 Ban"},
    {"index": 6, "side": "blue", "action": "pick", "label": "蓝方 1 Pick"},
    {"index": 7, "side": "red", "action": "pick", "label": "红方 1 Pick"},
    {"index": 8, "side": "red", "action": "pick", "label": "红方 2 Pick"},
    {"index": 9, "side": "blue", "action": "pick", "label": "蓝方 2 Pick"},
    {"index": 10, "side": "blue", "action": "pick", "label": "蓝方 3 Pick"},
    {"index": 11, "side": "red", "action": "pick", "label": "红方 3 Pick"},
    {"index": 12, "side": "red", "action": "ban", "label": "红方 4 Ban"},
    {"index": 13, "side": "blue", "action": "ban", "label": "蓝方 4 Ban"},
    {"index": 14, "side": "red", "action": "ban", "label": "红方 5 Ban"},
    {"index": 15, "side": "blue", "action": "ban", "label": "蓝方 5 Ban"},
    {"index": 16, "side": "red", "action": "pick", "label": "红方 4 Pick"},
    {"index": 17, "side": "blue", "action": "pick", "label": "蓝方 4 Pick"},
    {"index": 18, "side": "blue", "action": "pick", "label": "蓝方 5 Pick"},
    {"index": 19, "side": "red", "action": "pick", "label": "红方 5 Pick"},
]


def create_empty_game(game_number: int) -> Dict[str, Any]:
    return {
        "game_number": game_number,
        "blue_bans": [],
        "red_bans": [],
        "blue_picks": [],
        "red_picks": [],
        "turn_history": [],
        "status": "in_progress",
        "winner": None,
    }


def create_draft_session(blue_team_id: str, red_team_id: str, series_type: str = "BO3") -> Dict[str, Any]:
    if series_type not in ("BO1", "BO3", "BO5"):
        raise HTTPException(status_code=400, detail="series_type must be BO1, BO3, or BO5")

    conn = get_connection()
    try:
        cur = conn.cursor()
        # Verify teams exist
        cur.execute("SELECT id, name FROM teams WHERE id IN (?, ?)", (blue_team_id, red_team_id))
        found_teams = {r[0]: r[1] for r in cur.fetchall()}
        if blue_team_id not in found_teams:
            raise HTTPException(status_code=404, detail=f"Blue team '{blue_team_id}' not found")
        if red_team_id not in found_teams:
            raise HTTPException(status_code=404, detail=f"Red team '{red_team_id}' not found")

        draft_id = f"d_{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow().isoformat()
        initial_games = [create_empty_game(1)]

        cur.execute("""
        INSERT INTO drafts (
            id, blue_team_id, red_team_id, series_type, current_game,
            blue_score, red_score, status, series_picked_champions,
            games, current_turn_index, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            draft_id, blue_team_id, red_team_id, series_type, 1,
            0, 0, "in_progress", json.dumps([]),
            json.dumps(initial_games), 0, now, now
        ))
        conn.commit()
    finally:
        conn.close()

    return get_draft_state(draft_id)


def get_draft_state(draft_id: str) -> Dict[str, Any]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Draft session '{draft_id}' not found")
        data = row_to_dict(row)

        # Lookup team details
        cur.execute("SELECT id, name FROM teams WHERE id IN (?, ?)", (data["blue_team_id"], data["red_team_id"]))
        names = {r[0]: r[1] for r in cur.fetchall()}
        data["blue_team_name"] = names.get(data["blue_team_id"], "")
        data["red_team_name"] = names.get(data["red_team_id"], "")

        # Current turn info
        turn_idx = data["current_turn_index"]
        if turn_idx < len(DRAFT_TURNS):
            data["current_turn"] = DRAFT_TURNS[turn_idx]
            data["game_completed"] = False
        else:
            data["current_turn"] = None
            data["game_completed"] = True

        return data
    finally:
        conn.close()


def execute_action(draft_id: str, side: str, action: str, champion_id: str) -> Dict[str, Any]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Draft session '{draft_id}' not found")
        data = row_to_dict(row)

        if data["status"] == "completed":
            raise HTTPException(status_code=400, detail="Series is already completed")

        turn_idx = data["current_turn_index"]
        if turn_idx >= len(DRAFT_TURNS):
            raise HTTPException(status_code=400, detail="Current game draft is already finished; proceed to next game")

        expected_turn = DRAFT_TURNS[turn_idx]
        if expected_turn["side"] != side.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Turn mismatch: expected {expected_turn['side']} side turn, got {side}",
            )
        if expected_turn["action"] != action.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Action mismatch: expected {expected_turn['action']}, got {action}",
            )

        # Check champion exists
        cur.execute("SELECT id, name, role FROM champions WHERE id = ?", (champion_id,))
        champ_row = cur.fetchone()
        if not champ_row:
            raise HTTPException(status_code=404, detail=f"Champion '{champion_id}' not found")
        champ_name = champ_row[1]
        champ_role = champ_row[2]

        # 1. Global Fearless Draft check for picks:
        # Previously picked champions in earlier games of the series cannot be picked again
        series_picked = data.get("series_picked_champions", [])
        if action == "pick" and champion_id in series_picked:
            raise HTTPException(
                status_code=400,
                detail="champion already picked in this series (Fearless Draft)",
            )

        # 2. Check current game picks & bans
        games = data.get("games", [])
        curr_game = games[-1]
        all_current = curr_game["blue_bans"] + curr_game["red_bans"] + curr_game["blue_picks"] + curr_game["red_picks"]
        if any(c["champion_id"] == champion_id for c in all_current):
            raise HTTPException(
                status_code=400,
                detail=f"Champion '{champ_name}' has already been banned or picked in this game",
            )

        entry = {
            "turn_index": turn_idx,
            "side": side.lower(),
            "action": action.lower(),
            "champion_id": champion_id,
            "champion_name": champ_name,
            "role": champ_role,
        }

        if action == "ban":
            if side == "blue":
                curr_game["blue_bans"].append(entry)
            else:
                curr_game["red_bans"].append(entry)
        else:
            if side == "blue":
                curr_game["blue_picks"].append(entry)
            else:
                curr_game["red_picks"].append(entry)

        curr_game["turn_history"].append(entry)
        next_turn = turn_idx + 1

        if next_turn >= len(DRAFT_TURNS):
            curr_game["status"] = "completed"

        now = datetime.utcnow().isoformat()
        cur.execute("""
        UPDATE drafts
        SET games = ?, current_turn_index = ?, updated_at = ?
        WHERE id = ?
        """, (json.dumps(games), next_turn, now, draft_id))
        conn.commit()

        return get_draft_state(draft_id)
    finally:
        conn.close()


def advance_next_game(draft_id: str, winner: Optional[str] = None) -> Dict[str, Any]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Draft session '{draft_id}' not found")
        data = row_to_dict(row)

        if data["status"] == "completed":
            raise HTTPException(status_code=400, detail="Series is already completed")

        games = data.get("games", [])
        curr_game = games[-1]

        # Require current game draft to be finished
        if data["current_turn_index"] < len(DRAFT_TURNS):
            raise HTTPException(status_code=400, detail="Cannot advance: current game draft is not finished yet")

        # Record winner
        if winner in ("blue", "red"):
            curr_game["winner"] = winner
            if winner == "blue":
                data["blue_score"] += 1
            else:
                data["red_score"] += 1
        else:
            # Default to blue if unspecified
            curr_game["winner"] = "blue"
            data["blue_score"] += 1

        # Accumulate picked champions into series_picked_champions for Fearless rule
        series_picked = set(data.get("series_picked_champions", []))
        for p in curr_game["blue_picks"] + curr_game["red_picks"]:
            series_picked.add(p["champion_id"])
        new_series_picked = sorted(list(series_picked))

        # Check win condition
        win_threshold = 2 if data["series_type"] == "BO3" else (3 if data["series_type"] == "BO5" else 1)
        if data["blue_score"] >= win_threshold or data["red_score"] >= win_threshold:
            data["status"] = "completed"
        else:
            # Start next game
            next_game_num = len(games) + 1
            games.append(create_empty_game(next_game_num))
            data["current_game"] = next_game_num
            data["current_turn_index"] = 0

        now = datetime.utcnow().isoformat()
        cur.execute("""
        UPDATE drafts
        SET games = ?, current_game = ?, current_turn_index = ?,
            blue_score = ?, red_score = ?, status = ?,
            series_picked_champions = ?, updated_at = ?
        WHERE id = ?
        """, (
            json.dumps(games), data["current_game"], data["current_turn_index"],
            data["blue_score"], data["red_score"], data["status"],
            json.dumps(new_series_picked), now, draft_id
        ))
        conn.commit()

        return get_draft_state(draft_id)
    finally:
        conn.close()


def get_series_history(draft_id: str) -> Dict[str, Any]:
    state = get_draft_state(draft_id)
    return {
        "draft_id": state["id"],
        "series_type": state["series_type"],
        "blue_team": {"id": state["blue_team_id"], "name": state["blue_team_name"], "score": state["blue_score"]},
        "red_team": {"id": state["red_team_id"], "name": state["red_team_name"], "score": state["red_score"]},
        "status": state["status"],
        "series_picked_champions": state["series_picked_champions"],
        "total_games": len(state["games"]),
        "games": state["games"],
    }
