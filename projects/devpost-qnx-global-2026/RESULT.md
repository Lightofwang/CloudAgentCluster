# TraceLens for QNX — Project Implementation Result

**Project**: QNX Global Hackathon 2026: TraceLens — QNX 系统可观测性工作台  
**Hub Entry Slug**: `devpost-qnx-global-2026`  
**Track**: Developer Tooling & Host Tools (Best Use of QNX-specific Technologies)  
**Status**: Completed & Verified  

---

## 1. What Was Built

TraceLens is a target observability workbench engineered specifically for QNX Neutrino RTOS 8.0 developers. It bridges the gap between low-level kernel tracing and interactive developer tooling without requiring heavy IDEs like Momentics.

### Key Components

1. **High-Throughput Streaming QNX Trace Ingestion**:
   - Implemented in `app/qnx_trace.py`.
   - Streaming line-by-line parser consuming JSON Lines and QNX `slog2` log lines.
   - Models the core QNX 8.0 kernel trace abstractions:
     - `thread-state`: thread state transitions (`READY`, `RUNNING`, `BLOCKED`, `DEAD`), CPU core affinity, QNX priorities (1–255).
     - `kernel-call`: system call entry/exit records (`MsgSendv`, `MsgReceivev`, `SyncMutexLock`, `SyncMutexUnlock`).
     - `interrupt`: hardware interrupt service routine entry/exit and duration tracking.
     - `ipc-message`: QNX message-passing channels, sender/receiver thread IDs, message payloads, and round-trip latencies.
     - `pulse`: QNX lightweight, non-blocking 32-bit/64-bit atomic pulse notifications.
     - `slog2`: structured logging stream with severity levels and process tags.
   - Non-blocking error handling: malformed lines are tracked in `failed_lines` diagnostics without aborting valid event ingestion.

2. **Interactive HTML5 Canvas Scheduling Timeline**:
   - Implemented in `static/js/timeline_canvas.js`.
   - DPR-scaled high-resolution 2D Canvas rendering for crisp display on high-density monitors.
   - Renders color-coded thread scheduling blocks (`RUNNING` in QNX vibrant green, `READY` in amber, `BLOCKED` in slate gray).
   - Real-time overlay of hardware interrupt (IRQ) marker lines.
   - Smooth viewport navigation: wheel zooming (microsecond to multi-second window), drag-and-pan, dynamic time ruler, thread/process filtering.
   - Interactive hover tooltips showing state duration, start/end timestamps, process, and thread details.
   - One-click PNG export (`canvas.toDataURL()`).

3. **Performance Telemetry & Metrics Dashboards**:
   - Implemented in `app/services/stats.py` and `static/js/app.js`.
   - CPU duty cycle breakdown and state proportion bars per thread and process.
   - QNX IPC statistics: top channels by volume, pulse frequencies, and average `MsgSend`/`MsgReply` round-trip latencies.
   - Interrupt (IRQ) metrics: fire counts, cumulative execution duration, average duration, and peak execution times.

4. **Deterministic Anomaly Detection Rule Engine**:
   - Implemented in `app/services/anomalies.py` and `app/rules.py` with zero paid external APIs.
   - **Priority Inversion**: Flags when a high-priority thread is blocked on a mutex or resource held by a lower-priority thread exceeding threshold (100ms). Provides actionable remediation (recommending `PTHREAD_PRIO_INHERIT` priority inheritance mutexes).
   - **Deadline Miss**: Detects periodic tasks exceeding 1.5x expected period or violating timing bounds.
   - **Interrupt Storm**: Sliding 1-second window detecting IRQ triggers exceeding safe limits (>500/sec).
   - **Message Queue Backlog**: Detects unhandled message buildup in QNX communication channels (>20 messages).
   - Direct "在时间线中定位" jump button to zoom directly into the anomaly window on the timeline.

5. **Built-in Deterministic Trace Generator**:
   - Implemented in `app/generator.py`.
   - Seedable synthetic QNX trace generator creating multi-threaded workloads with configurable anomaly injection. Enables complete testing and demonstration without physical QNX target hardware.

6. **Target Hardware Capture Guide & Reference**:
   - Built-in documentation and web view covering QEMU x86_64 virtualization and Raspberry Pi 5 ARM64 physical board trace capture steps.

---

## 2. How to Run It

### Environment Requirements
- Python 3.11+
- Standard dependencies (FastAPI, uvicorn, pydantic, httpx, python-multipart)

### Quick Start Commands
```bash
# Navigate to the project directory
cd projects/devpost-qnx-global-2026

# Install requirements
pip install -r requirements.txt

# Start the workbench application
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser at `http://localhost:8000` to access the interactive web workbench.

### API Quick Verification (`curl`)
```bash
# 1. Health check
curl -s http://localhost:8000/api/health

# 2. Generate a synthetic QNX trace with all 4 anomaly types injected
curl -s -X POST http://localhost:8000/api/traces/generate \
  -H "Content-Type: application/json" \
  -d '{"threads": 8, "duration_seconds": 10, "inject": ["priority-inversion", "deadline-miss", "interrupt-storm", "message-queue-backlog"]}'

# 3. Retrieve anomalies detected
curl -s http://localhost:8000/api/traces/{trace_id}/anomalies

# 4. Fetch timeline visualization data
curl -s "http://localhost:8000/api/traces/{trace_id}/timeline?start_ns=0&end_ns=5000000000"

# 5. Retrieve CPU, IPC, and IRQ stats
curl -s http://localhost:8000/api/traces/{trace_id}/stats
```

---

## 3. Test & Verification Results

### Automated Unit & Integration Tests
Command executed:
```bash
cd projects/devpost-qnx-global-2026 && python3 -m unittest discover -s tests -v
```

Output:
```text
test_clean_trace_has_zero_anomalies (test_anomalies.TestAnomalyRulesEngine.test_clean_trace_has_zero_anomalies) ... ok
test_deadline_miss_minimal_reproduction (test_anomalies.TestAnomalyRulesEngine.test_deadline_miss_minimal_reproduction) ... ok
test_interrupt_storm_minimal_reproduction (test_anomalies.TestAnomalyRulesEngine.test_interrupt_storm_minimal_reproduction) ... ok
test_message_queue_backlog_minimal_reproduction (test_anomalies.TestAnomalyRulesEngine.test_message_queue_backlog_minimal_reproduction) ... ok
test_priority_inversion_minimal_reproduction (test_anomalies.TestAnomalyRulesEngine.test_priority_inversion_minimal_reproduction) ... ok
test_01_health_and_reference (test_api.TestTraceLensApi.test_01_health_and_reference) ... ok
test_02_generate_trace (test_api.TestTraceLensApi.test_02_generate_trace) ... ok
test_03_get_trace_by_id (test_api.TestTraceLensApi.test_03_get_trace_by_id) ... ok
test_04_get_trace_not_found (test_api.TestTraceLensApi.test_04_get_trace_not_found) ... ok
test_05_events_pagination_and_filtering (test_api.TestTraceLensApi.test_05_events_pagination_and_filtering) ... ok
test_06_timeline_endpoint (test_api.TestTraceLensApi.test_06_timeline_endpoint) ... ok
test_07_stats_endpoint (test_api.TestTraceLensApi.test_07_stats_endpoint) ... ok
test_08_anomalies_endpoint (test_api.TestTraceLensApi.test_08_anomalies_endpoint) ... ok
test_09_upload_trace_with_malformed_lines (test_api.TestTraceLensApi.test_09_upload_trace_with_malformed_lines) ... ok
test_10_delete_trace (test_api.TestTraceLensApi.test_10_delete_trace) ... ok
test_parse_error_handling (test_parser.TestQnxTraceParser.test_parse_error_handling) ... ok
test_parse_interrupt_valid (test_parser.TestQnxTraceParser.test_parse_interrupt_valid) ... ok
test_parse_ipc_message_valid (test_parser.TestQnxTraceParser.test_parse_ipc_message_valid) ... ok
test_parse_kernel_call_valid (test_parser.TestQnxTraceParser.test_parse_kernel_call_valid) ... ok
test_parse_pulse_valid (test_parser.TestQnxTraceParser.test_parse_pulse_valid) ... ok
test_parse_slog2_json_and_text (test_parser.TestQnxTraceParser.test_parse_slog2_json_and_text) ... ok
test_parse_thread_state_valid (test_parser.TestQnxTraceParser.test_parse_thread_state_valid) ... ok
test_streaming_large_dataset_performance (test_parser.TestQnxTraceParser.test_streaming_large_dataset_performance) ... ok
test_streaming_parse_with_failures (test_parser.TestQnxTraceParser.test_streaming_parse_with_failures) ... ok

----------------------------------------------------------------------
Ran 24 tests in 0.317s

OK
```
**Result**: 24/24 tests passed (100% pass rate).

### Performance Benchmarks
Command executed:
```bash
python3 projects/devpost-qnx-global-2026/tests/benchmark_perf.py
```

Output:
```text
=== TraceLens Performance Benchmarks ===
Generating 100,000 QNX trace lines...
Generated 100,000 lines (17.06 MB) in 0.45s
Uploading and streaming parsing into SQLite...
[PASS] 100,000 lines parsed and ingested in 2.006s (Target < 5.0s, Rate: 49854 lines/sec)
Benchmarking timeline endpoint p95 latency over 30 requests...
[PASS] Timeline Endpoint Latency: p50=4.3ms, p95=5.0ms (Target < 300ms)

>>> ALL PERFORMANCE BENCHMARKS PASSED! <<<
```

- **100,000 Lines Trace Ingestion**: **2.006 seconds** (Target was < 5.0 seconds).
- **Timeline Query Latency**: **p50 = 4.3ms, p95 = 5.0ms** (Target was < 300ms).

### Clean Environment Startup Check
Confirmed zero-dependency clean launch: `rm -f app.db && uvicorn main:app` starts up instantly, auto-initializes the SQLite database with WAL mode and schema indexes, and responds with `{"status": "ok"}` on `/api/health`.
