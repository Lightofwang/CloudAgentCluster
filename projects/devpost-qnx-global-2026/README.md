# TraceLens for QNX — QNX 8.0 Observability Workbench

TraceLens is an observability workbench engineered for QNX Neutrino RTOS 8.0 developers. It ingests target trace event streams and slog2 logs, visualizes multi-threaded scheduling timelines on an interactive HTML5 Canvas, computes CPU/IPC/Interrupt metrics, and automatically diagnoses critical real-time anomalies such as priority inversion, deadline misses, interrupt storms, and message queue backlogs.

Built for the **QNX Global Hackathon 2026** (Developer Tooling & Host Tools track).

---

## Key Features

1. **Streaming QNX Trace Ingestion**:
   - Parses structured QNX trace event streams (`thread-state`, `kernel-call`, `interrupt`, `ipc-message`, `pulse`, and `slog2` log lines).
   - High-throughput streaming parser with non-blocking error recovery (malformed lines are logged without failing the file ingestion).

2. **Interactive Canvas Timeline**:
   - Microsecond/nanosecond resolution scheduling view across CPU cores.
   - Color-coded thread state segments (`RUNNING`, `READY`, `BLOCKED`).
   - Overlay markers for hardware interrupts and system kernel calls.
   - Dynamic viewport zoom, pan, and thread filtering.

3. **Metrics & Performance Telemetry**:
   - CPU duty cycles and execution state breakdowns per thread and process.
   - QNX IPC statistics: channel throughput, pulse frequency, and MsgSend/MsgReply round-trip latencies.
   - Interrupt service counts and cumulative execution durations.

4. **Automated Anomaly Detection Engine**:
   - **Priority Inversion**: Detects high-priority threads blocked on low-priority resource owners.
   - **Deadline Miss**: Flags periodic task activation delays exceeding 1.5x expected period.
   - **Interrupt Storm**: Identifies interrupt flooding exceeding safe threshold in a 1-second rolling window.
   - **Message Queue Backlog**: Alerts on unhandled message accumulation in QNX channels.

5. **Built-in Deterministic Trace Generator**:
   - Generates realistic multi-threaded automotive/robotics trace streams with configurable anomaly injection for testing without physical QNX hardware.

---

## Architecture & Technology Stack

- **Backend**: Python 3.11+ / FastAPI / SQLite (WAL mode, indexed trace event queries).
- **Frontend**: Lightweight SPA (Native Vanilla JavaScript, HTML5 Canvas, CSS Grid/Flexbox, Dark Engineering Theme).
- **External Dependencies**: Zero paid APIs, 100% local execution.

---

## Quickstart

### 1. Installation
```bash
cd projects/devpost-qnx-global-2026
pip install -r requirements.txt
```

### 2. Launch Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser at `http://localhost:8000` to access the workbench UI.

---

## REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health status |
| `GET` | `/api/reference/event-types` | Schema reference for QNX trace event classes |
| `POST` | `/api/traces/upload` | Multipart upload of JSON Lines trace files |
| `POST` | `/api/traces/generate` | Generate deterministic synthetic QNX trace |
| `GET` | `/api/traces` | List ingested trace sessions |
| `GET` | `/api/traces/{trace_id}` | Retrieve trace metadata and parse diagnostics |
| `DELETE` | `/api/traces/{trace_id}` | Delete trace and associated events |
| `GET` | `/api/traces/{trace_id}/events` | Paginated query of raw trace events |
| `GET` | `/api/traces/{trace_id}/timeline` | Aggregated thread state intervals for canvas rendering |
| `GET` | `/api/traces/{trace_id}/stats` | CPU utilization, IPC metrics, and interrupt telemetry |
| `GET` | `/api/traces/{trace_id}/anomalies` | Detected real-time system anomalies and remediation tips |

### Command-Line API Examples (`curl`)

```bash
# 1. Health check
curl -s http://localhost:8000/api/health

# 2. Generate a synthetic QNX trace with all 4 anomaly types injected
curl -s -X POST http://localhost:8000/api/traces/generate \
  -H "Content-Type: application/json" \
  -d '{"threads": 8, "duration_seconds": 10, "inject": ["priority-inversion", "deadline-miss", "interrupt-storm", "message-queue-backlog"]}'

# 3. List ingested traces
curl -s http://localhost:8000/api/traces

# 4. Fetch detected anomalies for a trace session (replace {trace_id})
curl -s http://localhost:8000/api/traces/{trace_id}/anomalies

# 5. Fetch timeline state segments for rendering
curl -s "http://localhost:8000/api/traces/{trace_id}/timeline?start_ns=0&end_ns=5000000000"

# 6. Fetch CPU, IPC, and interrupt performance statistics
curl -s http://localhost:8000/api/traces/{trace_id}/stats

# 7. Upload a custom QNX target trace file
curl -s -X POST http://localhost:8000/api/traces/upload \
  -F "file=@qnx-target.trace.jsonl"
```

---

## Real QNX Target Capture Guide (QEMU & Raspberry Pi 5)

TraceLens consumes standard JSON Lines trace logs formatted according to QNX kernel event schemas. On actual QNX 8.0 target environments:

### Method A: QEMU QNX 8.0 x86_64 Target
1. Launch QNX target VM with tracing enabled (`qemu-system-x86_64 -M q35 -m 2G -kernel qnx-ifs.bin ...`).
2. Run `tracelogger -n 1 -f /dev/shmem/trace.raw` on the QNX target to capture system events into shared memory.
3. Use the QNX `traceprinter -v /dev/shmem/trace.raw` utility to export events or convert via the TraceLens collector bridge:
   ```bash
   qnx-trace-export --input /dev/shmem/trace.raw --format jsonl > qnx-target.trace.jsonl
   ```
4. Transfer `qnx-target.trace.jsonl` to your host machine and upload via TraceLens Web UI.

### Method B: Raspberry Pi 5 (ARM64 QNX Neutrino Target)
1. Boot QNX 8.0 BSP on Raspberry Pi 5.
2. Capture kernel events and slog2 logs:
   ```bash
   slog2info -w > /tmp/slog2.log &
   tracelogger -s 5 -f /tmp/qnx_pi5.trace
   ```
3. Format as TraceLens-compatible JSON Lines and import into the workbench.
