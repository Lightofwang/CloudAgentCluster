"""SQLite Database connection and initialization for DraftLens."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_FILE = os.getenv("DATABASE_PATH", str(Path(__file__).resolve().parent.parent / "data" / "draftlens.db"))


def get_db_path() -> Path:
    p = Path(DB_FILE)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def get_connection() -> sqlite3.Connection:
    path = get_db_path()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: Optional[sqlite3.Connection] = None) -> None:
    close_after = False
    if conn is None:
        conn = get_connection()
        close_after = True

    try:
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                region TEXT NOT NULL,
                style TEXT NOT NULL,
                win_rate REAL NOT NULL,
                avg_game_minutes REAL NOT NULL,
                objective_rates TEXT NOT NULL,
                first_blood_rate REAL NOT NULL,
                avg_vision_score REAL NOT NULL
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id TEXT PRIMARY KEY,
                team_id TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                kda REAL NOT NULL,
                champion_pool TEXT NOT NULL,
                recent_form TEXT NOT NULL,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS champions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                title TEXT NOT NULL,
                role TEXT NOT NULL,
                win_rate REAL NOT NULL,
                pick_rate REAL NOT NULL,
                ban_rate REAL NOT NULL,
                avatar_color TEXT NOT NULL
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id TEXT PRIMARY KEY,
                team_id TEXT NOT NULL,
                opponent_id TEXT NOT NULL,
                result TEXT NOT NULL,
                duration_minutes REAL NOT NULL,
                gold_diff_curve TEXT NOT NULL,
                objectives TEXT NOT NULL,
                first_blood INTEGER DEFAULT 1,
                vision_score REAL DEFAULT 75.0,
                played_at TEXT NOT NULL,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS matchups (
                champion_a TEXT NOT NULL,
                champion_b TEXT NOT NULL,
                winrate REAL NOT NULL,
                synergy REAL NOT NULL,
                counter REAL NOT NULL,
                PRIMARY KEY (champion_a, champion_b)
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS drafts (
                id TEXT PRIMARY KEY,
                blue_team_id TEXT NOT NULL,
                red_team_id TEXT NOT NULL,
                series_type TEXT NOT NULL,
                current_game INTEGER NOT NULL,
                blue_score INTEGER NOT NULL,
                red_score INTEGER NOT NULL,
                status TEXT NOT NULL,
                series_picked_champions TEXT NOT NULL,
                games TEXT NOT NULL,
                current_turn_index INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)
    finally:
        if close_after:
            conn.close()


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    for key in ("objective_rates", "champion_pool", "gold_diff_curve", "objectives", "series_picked_champions", "games"):
        if key in d and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except Exception:
                pass
    return d
