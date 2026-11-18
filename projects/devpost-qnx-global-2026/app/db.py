import json
import os
import sqlite3
from typing import Any, Dict, List, Optional

def get_db_path() -> str:
    return os.environ.get(
        "TRACELENS_DB_PATH",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.db")
    )

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    conn = sqlite3.connect(path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    init_db_if_needed(conn)
    return conn

def init_db_if_needed(conn: sqlite3.Connection) -> None:
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS traces (
            trace_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            total_lines INTEGER NOT NULL DEFAULT 0,
            parsed_events INTEGER NOT NULL DEFAULT 0,
            failed_lines TEXT NOT NULL DEFAULT '[]',
            start_ns INTEGER NOT NULL DEFAULT 0,
            end_ns INTEGER NOT NULL DEFAULT 0,
            threads INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT NOT NULL,
            timestamp_ns INTEGER NOT NULL,
            event_class TEXT NOT NULL,
            thread_id INTEGER,
            thread_name TEXT,
            process TEXT,
            cpu INTEGER DEFAULT 0,
            data TEXT NOT NULL,
            FOREIGN KEY (trace_id) REFERENCES traces(trace_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_events_trace_time ON events(trace_id, timestamp_ns);
        CREATE INDEX IF NOT EXISTS idx_events_trace_thread ON events(trace_id, thread_id);
        CREATE INDEX IF NOT EXISTS idx_events_trace_class ON events(trace_id, event_class);

        CREATE TABLE IF NOT EXISTS anomalies (
            id TEXT PRIMARY KEY,
            trace_id TEXT NOT NULL,
            type TEXT NOT NULL,
            severity TEXT NOT NULL,
            start_ns INTEGER NOT NULL,
            end_ns INTEGER NOT NULL,
            threads TEXT NOT NULL,
            description TEXT NOT NULL,
            suggestion TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (trace_id) REFERENCES traces(trace_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_anomalies_trace ON anomalies(trace_id);
        """)

def init_db(db_path: Optional[str] = None) -> None:
    path = db_path or get_db_path()
    conn = sqlite3.connect(path, timeout=30.0)
    init_db_if_needed(conn)
    conn.close()

def save_trace_metadata(conn: sqlite3.Connection, metadata: Dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO traces (
            trace_id, filename, total_lines, parsed_events, failed_lines,
            start_ns, end_ns, threads, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            metadata["trace_id"],
            metadata["filename"],
            metadata["total_lines"],
            metadata["parsed_events"],
            json.dumps(metadata.get("failed_lines", []), ensure_ascii=False),
            metadata.get("time_range", {}).get("start_ns", 0),
            metadata.get("time_range", {}).get("end_ns", 0),
            metadata.get("threads", 0),
            metadata["created_at"]
        )
    )

def batch_insert_events(conn: sqlite3.Connection, trace_id: str, events: List[Dict[str, Any]]) -> None:
    if not events:
        return
    rows = []
    for ev in events:
        data_dict = {k: v for k, v in ev.items() if k not in ("trace_id", "timestamp_ns", "event_class", "thread_id", "thread_name", "process", "cpu")}
        rows.append((
            trace_id,
            ev["timestamp_ns"],
            ev["event_class"],
            ev.get("thread_id"),
            ev.get("thread_name"),
            ev.get("process"),
            ev.get("cpu", 0),
            json.dumps(data_dict, ensure_ascii=False)
        ))
    conn.executemany(
        """
        INSERT INTO events (
            trace_id, timestamp_ns, event_class, thread_id, thread_name, process, cpu, data
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows
    )

def batch_insert_anomalies(conn: sqlite3.Connection, trace_id: str, anomalies: List[Dict[str, Any]]) -> None:
    if not anomalies:
        return
    rows = []
    for a in anomalies:
        rows.append((
            a["id"],
            trace_id,
            a["type"],
            a["severity"],
            a["start_ns"],
            a["end_ns"],
            json.dumps(a.get("threads", []), ensure_ascii=False),
            a["description"],
            a["suggestion"],
            a.get("created_at", "")
        ))
    conn.executemany(
        """
        INSERT OR REPLACE INTO anomalies (
            id, trace_id, type, severity, start_ns, end_ns, threads, description, suggestion, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows
    )

def get_trace_by_id(conn: sqlite3.Connection, trace_id: str) -> Optional[Dict[str, Any]]:
    cursor = conn.execute("SELECT * FROM traces WHERE trace_id = ?", (trace_id,))
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "trace_id": row["trace_id"],
        "filename": row["filename"],
        "total_lines": row["total_lines"],
        "parsed_events": row["parsed_events"],
        "failed_lines": json.loads(row["failed_lines"]),
        "time_range": {
            "start_ns": row["start_ns"],
            "end_ns": row["end_ns"]
        },
        "threads": row["threads"],
        "created_at": row["created_at"]
    }

def get_all_traces(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cursor = conn.execute("SELECT * FROM traces ORDER BY created_at DESC")
    results = []
    for row in cursor.fetchall():
        results.append({
            "trace_id": row["trace_id"],
            "filename": row["filename"],
            "total_lines": row["total_lines"],
            "parsed_events": row["parsed_events"],
            "failed_lines": json.loads(row["failed_lines"]),
            "time_range": {
                "start_ns": row["start_ns"],
                "end_ns": row["end_ns"]
            },
            "threads": row["threads"],
            "created_at": row["created_at"]
        })
    return results

def delete_trace_by_id(conn: sqlite3.Connection, trace_id: str) -> bool:
    with conn:
        cursor = conn.execute("DELETE FROM traces WHERE trace_id = ?", (trace_id,))
        conn.execute("DELETE FROM events WHERE trace_id = ?", (trace_id,))
        conn.execute("DELETE FROM anomalies WHERE trace_id = ?", (trace_id,))
        return cursor.rowcount > 0
