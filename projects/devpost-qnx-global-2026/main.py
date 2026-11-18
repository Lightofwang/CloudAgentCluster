import datetime
import io
import json
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.db import (
    batch_insert_anomalies,
    batch_insert_events,
    delete_trace_by_id,
    get_all_traces,
    get_connection,
    get_trace_by_id,
    init_db,
    save_trace_metadata
)
from app.generator import generate_qnx_trace_events
from app.qnx_trace import stream_parse_trace_lines
from app.services.anomalies import detect_anomalies
from app.services.stats import compute_trace_stats
from app.services.timeline import get_timeline_data

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI(
    title="TraceLens for QNX",
    description="Target System Observability Workbench for QNX 8.0 RTOS",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

# --- Health & Reference Endpoints ---

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/reference/event-types")
def get_event_types_reference():
    return {
        "event_classes": [
            {
                "name": "thread-state",
                "description": "QNX 线程调度状态变迁事件 (READY, RUNNING, BLOCKED, DEAD)",
                "fields": {
                    "timestamp_ns": "时间戳 (纳秒)",
                    "thread_id": "QNX 线程 ID (tid)",
                    "thread_name": "线程名",
                    "process": "所属进程名",
                    "old_state": "变迁前状态",
                    "new_state": "变迁后状态",
                    "cpu": "CPU 核心编号 (0, 1...)",
                    "priority": "可选，QNX 调度优先级 (1-255)"
                }
            },
            {
                "name": "kernel-call",
                "description": "QNX 内核调用进出记录 (MsgSendv, MsgReceivev, SyncMutexLock 等)",
                "fields": {
                    "timestamp_ns": "时间戳 (纳秒)",
                    "thread_id": "发起内核调用的线程 ID",
                    "thread_name": "线程名",
                    "process": "进程名",
                    "call_name": "系统调用名",
                    "entry_exit": "'entry' 进入 或 'exit' 退出",
                    "cpu": "执行 CPU 核心"
                }
            },
            {
                "name": "interrupt",
                "description": "硬件中断处理程序 (ISR) 触发与耗时",
                "fields": {
                    "timestamp_ns": "时间戳 (纳秒)",
                    "irq": "中断向量号 (IRQ ID)",
                    "entry_exit": "'entry' 或 'exit'",
                    "cpu": "触发 CPU 核心",
                    "duration_ns": "可选，中断执行耗时"
                }
            },
            {
                "name": "ipc-message",
                "description": "QNX 消息传递通道 (MsgSend / MsgReceive / MsgReply)",
                "fields": {
                    "timestamp_ns": "时间戳 (纳秒)",
                    "channel_id": "通道 ID (chid)",
                    "channel_name": "通道名称",
                    "sender_tid": "发送线程 ID",
                    "receiver_tid": "接收线程 ID",
                    "msg_type": "'send', 'receive', 或 'reply'",
                    "msg_size": "消息字节大小",
                    "roundtrip_ns": "可选，端到端往返耗时"
                }
            },
            {
                "name": "pulse",
                "description": "QNX 特有的轻量级定长非阻塞脉冲",
                "fields": {
                    "timestamp_ns": "时间戳 (纳秒)",
                    "channel_id": "目标通道 ID",
                    "code": "脉冲代码 (-128 到 127)",
                    "value": "脉冲负载数值"
                }
            },
            {
                "name": "slog2",
                "description": "QNX slog2 系统与驱动日志行",
                "fields": {
                    "timestamp_ns": "时间戳 (纳秒)",
                    "process": "记录日志的进程",
                    "thread_id": "可选，线程 ID",
                    "severity": "'info', 'warn', 或 'error'",
                    "message": "日志文本内容"
                }
            }
        ]
    }

# --- Trace Management Endpoints ---

class GenerateTraceRequest(BaseModel):
    threads: int = Field(default=8, ge=2, le=32)
    duration_seconds: int = Field(default=10, ge=1, le=60)
    inject: List[str] = Field(default_factory=lambda: ["priority-inversion", "deadline-miss"])
    seed: int = 42

@app.post("/api/traces/generate")
def generate_trace_endpoint(req: GenerateTraceRequest):
    trace_id = f"tr_{uuid.uuid4().hex[:8]}"
    filename = f"synthetic_qnx_t{req.threads}_{req.duration_seconds}s.trace.jsonl"
    created_at = datetime.datetime.utcnow().isoformat() + "Z"

    events_gen = generate_qnx_trace_events(
        threads_count=req.threads,
        duration_seconds=req.duration_seconds,
        inject=req.inject,
        seed=req.seed
    )

    all_events = list(events_gen)
    total_lines = len(all_events)
    parsed_events = total_lines
    min_ts = all_events[0]["timestamp_ns"] if all_events else 0
    max_ts = all_events[-1]["timestamp_ns"] if all_events else 0
    unique_tids = {e["thread_id"] for e in all_events if e.get("thread_id") is not None}

    metadata = {
        "trace_id": trace_id,
        "filename": filename,
        "total_lines": total_lines,
        "parsed_events": parsed_events,
        "failed_lines": [],
        "time_range": {"start_ns": min_ts, "end_ns": max_ts},
        "threads": len(unique_tids),
        "created_at": created_at
    }

    conn = get_connection()
    with conn:
        save_trace_metadata(conn, metadata)
        # Batch insert events in chunks of 2000
        for i in range(0, len(all_events), 2000):
            batch_insert_events(conn, trace_id, all_events[i:i + 2000])

        # Run anomaly detection and persist
        anomalies = detect_anomalies(conn, trace_id)
        batch_insert_anomalies(conn, trace_id, anomalies)
    conn.close()

    return metadata

@app.post("/api/traces/upload")
async def upload_trace_file(file: UploadFile = File(...)):
    # 50MB limit check
    MAX_SIZE = 50 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File size exceeds maximum limit of 50MB")

    trace_id = f"tr_{uuid.uuid4().hex[:8]}"
    filename = file.filename or "uploaded_qnx.trace.jsonl"
    created_at = datetime.datetime.utcnow().isoformat() + "Z"

    text_stream = io.StringIO(content.decode("utf-8", errors="replace"))

    conn = get_connection()
    stats = None

    try:
        with conn:
            # First create trace record to satisfy foreign key constraints
            save_trace_metadata(conn, {
                "trace_id": trace_id,
                "filename": filename,
                "total_lines": 0,
                "parsed_events": 0,
                "failed_lines": [],
                "time_range": {"start_ns": 0, "end_ns": 0},
                "threads": 0,
                "created_at": created_at
            })

            # We iterate through generator batches and insert
            parser_gen = stream_parse_trace_lines(text_stream, batch_size=2000)
            while True:
                try:
                    batch, current_stats = next(parser_gen)
                    batch_insert_events(conn, trace_id, batch)
                except StopIteration as stop:
                    stats = stop.value
                    break

            if not stats:
                stats = {
                    "total_lines": 0,
                    "parsed_events": 0,
                    "failed_lines": [],
                    "time_range": {"start_ns": 0, "end_ns": 0},
                    "threads": 0
                }

            metadata = {
                "trace_id": trace_id,
                "filename": filename,
                "total_lines": stats["total_lines"],
                "parsed_events": stats["parsed_events"],
                "failed_lines": stats["failed_lines"],
                "time_range": stats["time_range"],
                "threads": stats["threads"],
                "created_at": created_at
            }
            save_trace_metadata(conn, metadata)

            # Detect and persist anomalies
            anomalies = detect_anomalies(conn, trace_id)
            batch_insert_anomalies(conn, trace_id, anomalies)

    finally:
        conn.close()

    return metadata

@app.get("/api/traces")
def list_traces():
    conn = get_connection()
    try:
        traces = get_all_traces(conn)
        return traces
    finally:
        conn.close()

@app.get("/api/traces/{trace_id}")
def get_trace(trace_id: str):
    conn = get_connection()
    try:
        trace = get_trace_by_id(conn, trace_id)
        if not trace:
            raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
        return trace
    finally:
        conn.close()

@app.delete("/api/traces/{trace_id}")
def delete_trace(trace_id: str):
    conn = get_connection()
    try:
        deleted = delete_trace_by_id(conn, trace_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
        return {"status": "deleted", "trace_id": trace_id}
    finally:
        conn.close()

# --- Query, Timeline, Stats, and Anomalies Endpoints ---

@app.get("/api/traces/{trace_id}/events")
def get_trace_events(
    trace_id: str,
    thread_id: Optional[int] = Query(None),
    event_class: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    conn = get_connection()
    try:
        trace = get_trace_by_id(conn, trace_id)
        if not trace:
            raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")

        where_clauses = ["trace_id = ?"]
        params: List[Any] = [trace_id]

        if thread_id is not None:
            where_clauses.append("thread_id = ?")
            params.append(thread_id)
        if event_class:
            where_clauses.append("event_class = ?")
            params.append(event_class)

        where_sql = " AND ".join(where_clauses)

        # Count total matching
        count_cursor = conn.execute(f"SELECT COUNT(*) as cnt FROM events WHERE {where_sql}", params)
        total_count = count_cursor.fetchone()["cnt"]

        # Fetch page
        query_sql = f"""
        SELECT id, timestamp_ns, event_class, thread_id, thread_name, process, cpu, data
        FROM events
        WHERE {where_sql}
        ORDER BY timestamp_ns ASC, id ASC
        LIMIT ? OFFSET ?
        """
        cursor = conn.execute(query_sql, params + [limit, offset])
        events = []
        for r in cursor.fetchall():
            d = json.loads(r["data"]) if r["data"] else {}
            item = {
                "id": r["id"],
                "timestamp_ns": r["timestamp_ns"],
                "event_class": r["event_class"],
                "thread_id": r["thread_id"],
                "thread_name": r["thread_name"],
                "process": r["process"],
                "cpu": r["cpu"],
                **d
            }
            events.append(item)

        return {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "events": events
        }
    finally:
        conn.close()

@app.get("/api/traces/{trace_id}/timeline")
def get_trace_timeline(
    trace_id: str,
    start_ns: Optional[int] = Query(None),
    end_ns: Optional[int] = Query(None)
):
    conn = get_connection()
    try:
        trace = get_trace_by_id(conn, trace_id)
        if not trace:
            raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
        timeline = get_timeline_data(conn, trace_id, start_ns, end_ns)
        return timeline
    finally:
        conn.close()

@app.get("/api/traces/{trace_id}/stats")
def get_trace_statistics(trace_id: str):
    conn = get_connection()
    try:
        trace = get_trace_by_id(conn, trace_id)
        if not trace:
            raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
        stats = compute_trace_stats(conn, trace_id)
        return stats
    finally:
        conn.close()

@app.get("/api/traces/{trace_id}/anomalies")
def get_trace_anomalies(trace_id: str):
    conn = get_connection()
    try:
        trace = get_trace_by_id(conn, trace_id)
        if not trace:
            raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
        
        cursor = conn.execute(
            "SELECT id, type, severity, start_ns, end_ns, threads, description, suggestion FROM anomalies WHERE trace_id = ? ORDER BY start_ns ASC",
            (trace_id,)
        )
        anomalies = []
        for r in cursor.fetchall():
            anomalies.append({
                "id": r["id"],
                "type": r["type"],
                "severity": r["severity"],
                "start_ns": r["start_ns"],
                "end_ns": r["end_ns"],
                "threads": json.loads(r["threads"]) if r["threads"] else [],
                "description": r["description"],
                "suggestion": r["suggestion"]
            })
        return anomalies
    finally:
        conn.close()

# Mount Static Files
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "TraceLens Backend Running. Static files not found."}
