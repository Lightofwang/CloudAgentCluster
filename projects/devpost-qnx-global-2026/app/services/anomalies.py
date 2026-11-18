import json
import sqlite3
import uuid
from typing import Any, Dict, List

from app.rules import (
    INTERRUPT_STORM_THRESHOLD,
    INTERRUPT_STORM_WINDOW_NS,
    PRIORITY_INVERSION_THRESHOLD_NS,
    QUEUE_BACKLOG_COUNT_THRESHOLD,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
    SUGGESTIONS
)

def detect_anomalies(conn: sqlite3.Connection, trace_id: str) -> List[Dict[str, Any]]:
    """
    Evaluates rule engine across trace events and returns detected anomalies.
    """
    anomalies: List[Dict[str, Any]] = []

    # 1. Rule: Priority Inversion
    # Approach 1: Check thread-state blocking records with holder_thread / holder_tid
    block_rows = conn.execute(
        """
        SELECT timestamp_ns, thread_id, thread_name, process, data
        FROM events
        WHERE trace_id = ? AND event_class = 'thread-state'
        ORDER BY thread_id, timestamp_ns ASC
        """,
        (trace_id,)
    ).fetchall()

    thread_blocks: Dict[int, List[Dict[str, Any]]] = {}
    for r in block_rows:
        tid = r["thread_id"]
        if tid not in thread_blocks:
            thread_blocks[tid] = []
        data = json.loads(r["data"]) if r["data"] else {}
        thread_blocks[tid].append({
            "ts": r["timestamp_ns"],
            "thread_name": r["thread_name"] or f"tid-{tid}",
            "process": r["process"] or "unknown",
            "old_state": data.get("old_state"),
            "new_state": data.get("new_state"),
            "priority": data.get("priority", 0),
            "data": data
        })

    for tid, states in thread_blocks.items():
        blocked_start = None
        blocked_info = None

        for st in states:
            if st["new_state"] == "BLOCKED":
                data = st["data"]
                # If explicit holder or mutex block is indicated
                if "holder_thread" in data or "mutex_id" in data or "block_reason" in data:
                    blocked_start = st["ts"]
                    blocked_info = st
            elif st["new_state"] in ("READY", "RUNNING") and blocked_start is not None:
                duration_ns = st["ts"] - blocked_start
                if duration_ns >= PRIORITY_INVERSION_THRESHOLD_NS:
                    holder = blocked_info["data"].get("holder_thread", "lower-priority task")
                    high_th = blocked_info["thread_name"]
                    anomalies.append({
                        "id": f"an_pi_{uuid.uuid4().hex[:8]}",
                        "type": "priority-inversion",
                        "severity": SEVERITY_HIGH,
                        "start_ns": blocked_start,
                        "end_ns": st["ts"],
                        "threads": [high_th, holder],
                        "description": f"高优先级线程 {high_th} (优先级 {blocked_info['priority']}) 被低优先级线程 {holder} 阻塞 {duration_ns // 1_000_000}ms",
                        "suggestion": SUGGESTIONS["priority-inversion"]
                    })
                blocked_start = None
                blocked_info = None

    # Approach 2: Check mutex lock entry/exit kernel calls if not detected yet
    if not any(a["type"] == "priority-inversion" for a in anomalies):
        mutex_calls = conn.execute(
            """
            SELECT timestamp_ns, thread_id, thread_name, process, data
            FROM events
            WHERE trace_id = ? AND event_class = 'kernel-call'
            ORDER BY timestamp_ns ASC
            """,
            (trace_id,)
        ).fetchall()

        mutex_holders: Dict[int, Dict[str, Any]] = {}
        for mc in mutex_calls:
            data = json.loads(mc["data"]) if mc["data"] else {}
            call_name = data.get("call_name")
            entry_exit = data.get("entry_exit")
            mid = data.get("mutex_id")
            if not mid:
                continue

            if call_name == "SyncMutexLock" and entry_exit == "exit":
                mutex_holders[mid] = {
                    "tid": mc["thread_id"],
                    "name": mc["thread_name"],
                    "ts": mc["timestamp_ns"]
                }
            elif call_name == "SyncMutexUnlock" and entry_exit == "entry":
                if mid in mutex_holders:
                    del mutex_holders[mid]

    # 2. Rule: Deadline Miss
    # Detect periodic execution gaps exceeding expected period by 1.5x
    # or from slog2 deadline warnings
    slog_rows = conn.execute(
        """
        SELECT timestamp_ns, thread_id, thread_name, process, data
        FROM events
        WHERE trace_id = ? AND event_class = 'slog2'
        ORDER BY timestamp_ns ASC
        """,
        (trace_id,)
    ).fetchall()

    for sr in slog_rows:
        data = json.loads(sr["data"]) if sr["data"] else {}
        msg = data.get("message", "").lower()
        if "deadline" in msg and ("miss" in msg or "exceeded" in msg or "delay" in msg):
            anomalies.append({
                "id": f"an_dl_{uuid.uuid4().hex[:8]}",
                "type": "deadline-miss",
                "severity": SEVERITY_HIGH,
                "start_ns": max(0, sr["timestamp_ns"] - 100_000_000),
                "end_ns": sr["timestamp_ns"],
                "threads": [sr["thread_name"] or sr["process"]],
                "description": f"任务 {sr['thread_name'] or sr['process']} 周期执行超时错失截止期: {data.get('message')}",
                "suggestion": SUGGESTIONS["deadline-miss"]
            })

    # Check state intervals for periodic threads if no slog2 deadline found
    if not any(a["type"] == "deadline-miss" for a in anomalies):
        for tid, states in thread_blocks.items():
            run_starts = [st["ts"] for st in states if st["new_state"] == "RUNNING"]
            if len(run_starts) >= 4:
                intervals = [run_starts[i] - run_starts[i - 1] for i in range(1, len(run_starts))]
                median_interval = sorted(intervals)[len(intervals) // 2]
                for i, iv in enumerate(intervals):
                    if iv > median_interval * 1.5 and iv > 30_000_000:
                        t_name = states[0]["thread_name"]
                        anomalies.append({
                            "id": f"an_dl_{uuid.uuid4().hex[:8]}",
                            "type": "deadline-miss",
                            "severity": SEVERITY_HIGH,
                            "start_ns": run_starts[i],
                            "end_ns": run_starts[i + 1],
                            "threads": [t_name],
                            "description": f"周期线程 {t_name} 实际运行间隔 ({iv // 1_000_000}ms) 超过预期周期 ({median_interval // 1_000_000}ms) 1.5倍",
                            "suggestion": SUGGESTIONS["deadline-miss"]
                        })
                        break

    # 3. Rule: Interrupt Storm
    # 1-second rolling window with count > INTERRUPT_STORM_THRESHOLD (500)
    irq_rows = conn.execute(
        """
        SELECT timestamp_ns, data
        FROM events
        WHERE trace_id = ? AND event_class = 'interrupt'
        ORDER BY timestamp_ns ASC
        """,
        (trace_id,)
    ).fetchall()

    irqs_by_num: Dict[int, List[int]] = {}
    for ir in irq_rows:
        data = json.loads(ir["data"]) if ir["data"] else {}
        irq_num = data.get("irq", 0)
        if irq_num not in irqs_by_num:
            irqs_by_num[irq_num] = []
        irqs_by_num[irq_num].append(ir["timestamp_ns"])

    for irq_num, timestamps in irqs_by_num.items():
        if len(timestamps) < INTERRUPT_STORM_THRESHOLD:
            continue

        left = 0
        storm_detected = False
        for right in range(len(timestamps)):
            while timestamps[right] - timestamps[left] > INTERRUPT_STORM_WINDOW_NS:
                left += 1
            count_in_window = right - left + 1
            if count_in_window >= INTERRUPT_STORM_THRESHOLD and not storm_detected:
                storm_start = timestamps[left]
                storm_end = timestamps[right]
                anomalies.append({
                    "id": f"an_irq_{uuid.uuid4().hex[:8]}",
                    "type": "interrupt-storm",
                    "severity": SEVERITY_CRITICAL,
                    "start_ns": storm_start,
                    "end_ns": storm_end,
                    "threads": [f"IRQ-{irq_num}"],
                    "description": f"硬件中断 IRQ {irq_num} 在 1 秒窗口内触发 {count_in_window} 次，超过安全阈值 ({INTERRUPT_STORM_THRESHOLD} 次/秒)",
                    "suggestion": SUGGESTIONS["interrupt-storm"]
                })
                storm_detected = True
                break

    # 4. Rule: Message Queue Backlog
    # Check pending_queue_size or slog2 channel backlog warnings
    ipc_backlog_rows = conn.execute(
        """
        SELECT timestamp_ns, data
        FROM events
        WHERE trace_id = ? AND event_class = 'ipc-message'
        ORDER BY timestamp_ns ASC
        """,
        (trace_id,)
    ).fetchall()

    max_backlog = 0
    backlog_chan = ""
    backlog_start = 0
    backlog_end = 0

    for r in ipc_backlog_rows:
        data = json.loads(r["data"]) if r["data"] else {}
        qsize = data.get("pending_queue_size", 0)
        if qsize >= QUEUE_BACKLOG_COUNT_THRESHOLD:
            if max_backlog == 0:
                backlog_start = r["timestamp_ns"]
                backlog_chan = data.get("channel_name", f"chan-{data.get('channel_id', 0)}")
            if qsize > max_backlog:
                max_backlog = qsize
            backlog_end = r["timestamp_ns"]

    if max_backlog >= QUEUE_BACKLOG_COUNT_THRESHOLD:
        anomalies.append({
            "id": f"an_bk_{uuid.uuid4().hex[:8]}",
            "type": "message-queue-backlog",
            "severity": SEVERITY_MEDIUM,
            "start_ns": backlog_start,
            "end_ns": max(backlog_end, backlog_start + 50_000_000),
            "threads": [backlog_chan, "msg-broker"],
            "description": f"IPC 通道 {backlog_chan} 堆积 {max_backlog} 条未处理消息，持续超过积压阈值 ({QUEUE_BACKLOG_COUNT_THRESHOLD} 条)",
            "suggestion": SUGGESTIONS["message-queue-backlog"]
        })

    # Sort anomalies by severity priority
    sev_order = {
        SEVERITY_CRITICAL: 0,
        SEVERITY_HIGH: 1,
        SEVERITY_MEDIUM: 2,
        SEVERITY_LOW: 3
    }
    anomalies.sort(key=lambda a: (sev_order.get(a["severity"], 99), a["start_ns"]))

    return anomalies
