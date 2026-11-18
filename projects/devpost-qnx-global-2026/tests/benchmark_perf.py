import io
import json
import os
import sys
import time

proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, proj_root)

from fastapi.testclient import TestClient
from main import app
from app.db import init_db

def run_performance_benchmarks():
    print("=== TraceLens Performance Benchmarks ===")
    bench_db = f"/tmp/bench_{int(time.time())}.db"
    os.environ["TRACELENS_DB_PATH"] = bench_db
    init_db(bench_db)
    client = TestClient(app)

    # 1. Generate 100,000 lines in memory
    print("Generating 100,000 QNX trace lines...")
    t0 = time.perf_counter()
    lines = []
    for i in range(100_000):
        tid = (i % 8) + 1
        lines.append(json.dumps({
            "timestamp_ns": i * 100_000,
            "event_class": "thread-state",
            "thread_id": tid,
            "thread_name": f"worker-{tid}",
            "process": f"svc-{(tid % 3) + 1}",
            "old_state": "READY" if i % 2 == 0 else "RUNNING",
            "new_state": "RUNNING" if i % 2 == 0 else "READY",
            "cpu": tid % 2
        }))
    content = "\n".join(lines).encode("utf-8")
    gen_duration = time.perf_counter() - t0
    print(f"Generated 100,000 lines ({len(content) / (1024*1024):.2f} MB) in {gen_duration:.2f}s")

    # 2. Upload and Parse benchmark (< 5s target)
    print("Uploading and streaming parsing into SQLite...")
    files = {"file": ("bench_100k.trace.jsonl", content, "application/x-jsonlines")}
    t_start = time.perf_counter()
    res = client.post("/api/traces/upload", files=files)
    parse_duration = time.perf_counter() - t_start
    assert res.status_code == 200, f"Upload benchmark failed: {res.text}"
    up_data = res.json()
    assert up_data["total_lines"] == 100_000
    assert up_data["parsed_events"] == 100_000
    print(f"[PASS] 100,000 lines parsed and ingested in {parse_duration:.3f}s (Target < 5.0s, Rate: {100_000/parse_duration:.0f} lines/sec)")
    assert parse_duration < 5.0, f"Parse duration {parse_duration:.2f}s exceeded 5s limit!"

    trace_id = up_data["trace_id"]

    # 3. Timeline query p95 latency benchmark (< 300ms target)
    latencies = []
    print("Benchmarking timeline endpoint p95 latency over 30 requests...")
    for _ in range(30):
        t_req = time.perf_counter()
        res = client.get(f"/api/traces/{trace_id}/timeline")
        req_dur = (time.perf_counter() - t_req) * 1000.0  # in ms
        assert res.status_code == 200
        latencies.append(req_dur)

    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    print(f"[PASS] Timeline Endpoint Latency: p50={p50:.1f}ms, p95={p95:.1f}ms (Target < 300ms)")
    assert p95 < 300.0, f"p95 latency {p95:.1f}ms exceeded 300ms limit!"

    # Clean up
    if os.path.exists(bench_db):
        os.remove(bench_db)

    print("\n>>> ALL PERFORMANCE BENCHMARKS PASSED! <<<")

if __name__ == "__main__":
    run_performance_benchmarks()
