import json
import sqlite3
from typing import Any, Dict, List

def compute_trace_stats(conn: sqlite3.Connection, trace_id: str) -> Dict[str, Any]:
    trace_row = conn.execute(
        "SELECT start_ns, end_ns FROM traces WHERE trace_id = ?",
        (trace_id,)
    ).fetchone()
    if not trace_row:
        return {"cpu": [], "ipc": {}, "interrupts": []}

    total_trace_duration_ns = max(1, trace_row["end_ns"] - trace_row["start_ns"])

    # 1. CPU & Thread State Breakdown
    # Fetch thread states
    state_rows = conn.execute(
        """
        SELECT timestamp_ns, thread_id, thread_name, process, data
        FROM events
        WHERE trace_id = ? AND event_class = 'thread-state'
        ORDER BY thread_id, timestamp_ns ASC
        """,
        (trace_id,)
    ).fetchall()

    thread_time_acc: Dict[int, Dict[str, Any]] = {}
    last_event: Dict[int, Dict[str, Any]] = {}

    for r in state_rows:
        tid = r["thread_id"]
        ts = r["timestamp_ns"]
        data = json.loads(r["data"]) if r["data"] else {}
        new_state = data.get("new_state", "READY")

        if tid not in thread_time_acc:
            thread_time_acc[tid] = {
                "thread_id": tid,
                "thread_name": r["thread_name"] or f"tid-{tid}",
                "process": r["process"] or "unknown",
                "running_ns": 0,
                "ready_ns": 0,
                "blocked_ns": 0,
            }

        if tid in last_event:
            prev_ts = last_event[tid]["ts"]
            prev_state = last_event[tid]["state"]
            delta = max(0, ts - prev_ts)

            if prev_state == "RUNNING":
                thread_time_acc[tid]["running_ns"] += delta
            elif prev_state == "READY":
                thread_time_acc[tid]["ready_ns"] += delta
            elif prev_state == "BLOCKED":
                thread_time_acc[tid]["blocked_ns"] += delta

        last_event[tid] = {"ts": ts, "state": new_state}

    cpu_stats: List[Dict[str, Any]] = []
    total_cpu_running_ns = sum(t["running_ns"] for t in thread_time_acc.values())

    for tid, info in thread_time_acc.items():
        running_ns = info["running_ns"]
        ready_ns = info["ready_ns"]
        blocked_ns = info["blocked_ns"]
        total_recorded = max(1, running_ns + ready_ns + blocked_ns)
        
        # CPU usage percent relative to total trace duration
        cpu_pct = round((running_ns / total_trace_duration_ns) * 100, 2)
        
        cpu_stats.append({
            "thread_id": tid,
            "thread_name": info["thread_name"],
            "process": info["process"],
            "running_ns": running_ns,
            "ready_ns": ready_ns,
            "blocked_ns": blocked_ns,
            "running_pct": round((running_ns / total_recorded) * 100, 1),
            "ready_pct": round((ready_ns / total_recorded) * 100, 1),
            "blocked_pct": round((blocked_pct := blocked_ns / total_recorded) * 100, 1),
            "cpu_usage_pct": cpu_pct
        })

    # Sort CPU stats by running_ns descending
    cpu_stats.sort(key=lambda x: x["running_ns"], reverse=True)

    # 2. IPC Statistics
    ipc_rows = conn.execute(
        """
        SELECT event_class, data
        FROM events
        WHERE trace_id = ? AND event_class IN ('ipc-message', 'pulse')
        """,
        (trace_id,)
    ).fetchall()

    channel_stats: Dict[int, Dict[str, Any]] = {}
    total_messages = 0
    total_pulses = 0

    for r in ipc_rows:
        cls = r["event_class"]
        data = json.loads(r["data"]) if r["data"] else {}
        cid = data.get("channel_id", 0)
        cname = data.get("channel_name", f"chan-{cid}")

        if cid not in channel_stats:
            channel_stats[cid] = {
                "channel_id": cid,
                "channel_name": cname,
                "message_count": 0,
                "pulse_count": 0,
                "roundtrips": []
            }

        if cls == "ipc-message":
            total_messages += 1
            channel_stats[cid]["message_count"] += 1
            if "roundtrip_ns" in data and data["roundtrip_ns"] > 0:
                channel_stats[cid]["roundtrips"].append(data["roundtrip_ns"])
        elif cls == "pulse":
            total_pulses += 1
            channel_stats[cid]["pulse_count"] += 1

    channels_list = []
    for cid, cinfo in channel_stats.items():
        rt_list = cinfo["roundtrips"]
        avg_rt = round(sum(rt_list) / len(rt_list), 0) if rt_list else 0
        channels_list.append({
            "channel_id": cid,
            "channel_name": cinfo["channel_name"],
            "message_count": cinfo["message_count"],
            "pulse_count": cinfo["pulse_count"],
            "avg_roundtrip_ns": int(avg_rt)
        })
    channels_list.sort(key=lambda c: (c["message_count"] + c["pulse_count"]), reverse=True)

    ipc_summary = {
        "total_messages": total_messages,
        "total_pulses": total_pulses,
        "channels": channels_list
    }

    # 3. Interrupt Statistics
    irq_rows = conn.execute(
        """
        SELECT data
        FROM events
        WHERE trace_id = ? AND event_class = 'interrupt'
        """,
        (trace_id,)
    ).fetchall()

    irq_acc: Dict[int, List[int]] = {}
    for r in irq_rows:
        data = json.loads(r["data"]) if r["data"] else {}
        irq = data.get("irq", 0)
        dur = data.get("duration_ns", 10_000)
        if irq not in irq_acc:
            irq_acc[irq] = []
        irq_acc[irq].append(dur)

    interrupt_stats = []
    for irq, durations in irq_acc.items():
        cnt = len(durations)
        tot_dur = sum(durations)
        avg_dur = round(tot_dur / cnt, 1)
        max_dur = max(durations)
        interrupt_stats.append({
            "irq": irq,
            "count": cnt,
            "total_duration_ns": tot_dur,
            "avg_duration_ns": avg_dur,
            "max_duration_ns": max_dur
        })
    interrupt_stats.sort(key=lambda x: x["count"], reverse=True)

    return {
        "cpu": cpu_stats,
        "ipc": ipc_summary,
        "interrupts": interrupt_stats
    }
