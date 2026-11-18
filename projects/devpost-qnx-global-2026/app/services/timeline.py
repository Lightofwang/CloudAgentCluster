import json
import sqlite3
from typing import Any, Dict, List, Optional

def get_timeline_data(
    conn: sqlite3.Connection,
    trace_id: str,
    start_ns: Optional[int] = None,
    end_ns: Optional[int] = None
) -> Dict[str, Any]:
    """
    Computes aggregated thread execution intervals and interrupt markers for canvas rendering.
    """
    # 1. Fetch trace time bounds if start_ns/end_ns not fully specified
    if start_ns is None or end_ns is None:
        trace_row = conn.execute(
            "SELECT start_ns, end_ns FROM traces WHERE trace_id = ?",
            (trace_id,)
        ).fetchone()
        if trace_row:
            if start_ns is None:
                start_ns = trace_row["start_ns"]
            if end_ns is None:
                end_ns = trace_row["end_ns"]
        else:
            start_ns = start_ns or 0
            end_ns = end_ns or 0

    # Ensure start_ns <= end_ns
    if end_ns < start_ns:
        start_ns, end_ns = end_ns, start_ns

    # 2. Query thread state events ordered by thread and timestamp
    query = """
    SELECT timestamp_ns, thread_id, thread_name, process, data
    FROM events
    WHERE trace_id = ? AND event_class = 'thread-state'
    ORDER BY thread_id, timestamp_ns ASC
    """
    rows = conn.execute(query, (trace_id,)).fetchall()

    # Group by thread
    thread_events: Dict[int, List[Dict[str, Any]]] = {}
    thread_meta: Dict[int, Dict[str, str]] = {}

    for r in rows:
        tid = r["thread_id"]
        if tid not in thread_events:
            thread_events[tid] = []
            thread_meta[tid] = {
                "thread_id": tid,
                "thread_name": r["thread_name"] or f"tid-{tid}",
                "process": r["process"] or "unknown"
            }
        data = json.loads(r["data"]) if r["data"] else {}
        thread_events[tid].append({
            "ts": r["timestamp_ns"],
            "new_state": data.get("new_state", "READY"),
            "old_state": data.get("old_state", "READY"),
            "data": data
        })

    threads_timeline = []

    for tid, meta in thread_meta.items():
        ev_list = thread_events[tid]
        if not ev_list:
            continue

        raw_segments = []
        for i in range(len(ev_list)):
            cur = ev_list[i]
            cur_ts = cur["ts"]
            state = cur["new_state"]
            next_ts = ev_list[i + 1]["ts"] if i + 1 < len(ev_list) else end_ns

            if next_ts <= cur_ts:
                continue

            # Clip to query window [start_ns, end_ns]
            seg_start = max(cur_ts, start_ns)
            seg_end = min(next_ts, end_ns)

            if seg_end > seg_start:
                raw_segments.append({
                    "start_ns": seg_start,
                    "end_ns": seg_end,
                    "state": state
                })

        # Merge adjacent segments with identical state
        merged_segments = []
        for seg in raw_segments:
            if merged_segments and merged_segments[-1]["state"] == seg["state"] and merged_segments[-1]["end_ns"] == seg["start_ns"]:
                merged_segments[-1]["end_ns"] = seg["end_ns"]
            else:
                merged_segments.append(seg)

        threads_timeline.append({
            "thread_id": meta["thread_id"],
            "thread_name": meta["thread_name"],
            "process": meta["process"],
            "segments": merged_segments
        })

    # Sort threads deterministically by thread_id
    threads_timeline.sort(key=lambda t: t["thread_id"])

    # 3. Query interrupts within window
    irq_rows = conn.execute(
        """
        SELECT timestamp_ns, data
        FROM events
        WHERE trace_id = ? AND event_class = 'interrupt' AND timestamp_ns BETWEEN ? AND ?
        ORDER BY timestamp_ns ASC
        LIMIT 5000
        """,
        (trace_id, start_ns, end_ns)
    ).fetchall()

    interrupts = []
    for r in irq_rows:
        data = json.loads(r["data"]) if r["data"] else {}
        interrupts.append({
            "timestamp_ns": r["timestamp_ns"],
            "irq": data.get("irq", 0),
            "duration_ns": data.get("duration_ns", 10_000)
        })

    return {
        "threads": threads_timeline,
        "interrupts": interrupts
    }
