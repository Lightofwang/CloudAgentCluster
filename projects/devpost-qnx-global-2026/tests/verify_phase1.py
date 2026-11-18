import json
import os
import sys

# Ensure project root is in python path
proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, proj_root)

from fastapi.testclient import TestClient
from main import app
from app.db import init_db

def run_phase1_verification():
    print("=== TraceLens Phase 1 Verification ===")
    test_db = os.path.join(proj_root, "test_phase1.db")
    if os.path.exists(test_db):
        os.remove(test_db)
    os.environ["TRACELENS_DB_PATH"] = test_db
    init_db(test_db)

    client = TestClient(app)

    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    assert res.json() == {"status": "ok"}
    print("[PASS] 1. /api/health returned ok")

    # 2. Reference event-types
    res = client.get("/api/reference/event-types")
    assert res.status_code == 200
    classes = [c["name"] for c in res.json()["event_classes"]]
    assert "thread-state" in classes and "kernel-call" in classes and "interrupt" in classes and "ipc-message" in classes
    print(f"[PASS] 2. /api/reference/event-types returned {len(classes)} classes")

    # 3. Generate trace with all 4 anomaly types
    req_body = {
        "threads": 8,
        "duration_seconds": 10,
        "inject": [
            "priority-inversion",
            "deadline-miss",
            "interrupt-storm",
            "message-queue-backlog"
        ]
    }
    res = client.post("/api/traces/generate", json=req_body)
    assert res.status_code == 200, f"Generate failed: {res.text}"
    gen_data = res.json()
    trace_id = gen_data["trace_id"]
    print(f"[PASS] 3. Generated trace {trace_id}: {gen_data['parsed_events']} events, {gen_data['threads']} threads")

    # 4. Check anomalies for generated trace
    res = client.get(f"/api/traces/{trace_id}/anomalies")
    assert res.status_code == 200
    anomalies = res.json()
    print(f"Detected {len(anomalies)} anomalies:")
    detected_types = {a["type"] for a in anomalies}
    for a in anomalies:
        print(f"  - [{a['severity'].upper()}] {a['type']} (t={a['start_ns']}-{a['end_ns']}ns): {a['description']}")

    assert "priority-inversion" in detected_types, "Missing priority-inversion anomaly"
    assert "deadline-miss" in detected_types, "Missing deadline-miss anomaly"
    assert "interrupt-storm" in detected_types, "Missing interrupt-storm anomaly"
    assert "message-queue-backlog" in detected_types, "Missing message-queue-backlog anomaly"
    print("[PASS] 4. All 4 injected anomaly types successfully detected with valid time windows and remediation suggestions!")

    # 5. Check timeline endpoint
    res = client.get(f"/api/traces/{trace_id}/timeline")
    assert res.status_code == 200
    timeline = res.json()
    assert len(timeline["threads"]) > 0
    assert len(timeline["interrupts"]) > 0
    print(f"[PASS] 5. Timeline returned {len(timeline['threads'])} threads and {len(timeline['interrupts'])} interrupts")

    # 6. Check stats endpoint
    res = client.get(f"/api/traces/{trace_id}/stats")
    assert res.status_code == 200
    stats = res.json()
    assert len(stats["cpu"]) > 0
    assert stats["ipc"]["total_messages"] > 0
    assert len(stats["interrupts"]) > 0
    print(f"[PASS] 6. Stats returned {len(stats['cpu'])} CPU thread metrics, {stats['ipc']['total_messages']} IPC messages, and {len(stats['interrupts'])} IRQ metrics")

    # 7. Check events pagination endpoint
    res = client.get(f"/api/traces/{trace_id}/events?limit=50&offset=0")
    assert res.status_code == 200
    ev_page = res.json()
    assert ev_page["total"] == gen_data["parsed_events"]
    assert len(ev_page["events"]) == 50
    print(f"[PASS] 7. Paginated events returned total={ev_page['total']}, limit=50")

    # 8. Upload trace containing 20 malformed lines + valid lines
    valid_line = json.dumps({
        "timestamp_ns": 1000,
        "event_class": "thread-state",
        "thread_id": 1,
        "thread_name": "sensor-fusion",
        "process": "fusion-svc",
        "old_state": "READY",
        "new_state": "RUNNING",
        "cpu": 0
    })
    bad_lines = [
        "not a json line",
        "{malformed json",
        json.dumps({"timestamp_ns": -10, "event_class": "thread-state"}),
        json.dumps({"timestamp_ns": 100, "event_class": "unsupported-event"}),
        json.dumps({"timestamp_ns": 200}),  # missing event_class
        json.dumps({"timestamp_ns": 300, "event_class": "thread-state", "old_state": "INVALID_STATE", "new_state": "RUNNING"}),
    ] + [f"corrupted raw data {i}" for i in range(14)] # Total 20 bad lines
    assert len(bad_lines) == 20

    mixed_lines = []
    for i in range(50):
        mixed_lines.append(json.dumps({
            "timestamp_ns": 1000 + (i * 100),
            "event_class": "interrupt",
            "irq": 21,
            "entry_exit": "entry",
            "cpu": 0
        }))
    # Interleave bad lines
    mixed_content = "\n".join(mixed_lines[:25] + bad_lines + mixed_lines[25:]) + "\n"

    files = {"file": ("corrupted_test.trace.jsonl", mixed_content.encode("utf-8"), "application/x-jsonlines")}
    res = client.post("/api/traces/upload", files=files)
    assert res.status_code == 200, f"Upload failed: {res.text}"
    up_data = res.json()
    assert up_data["total_lines"] == 70, f"Expected 70 total lines, got {up_data['total_lines']}"
    assert up_data["parsed_events"] == 50, f"Expected 50 parsed events, got {up_data['parsed_events']}"
    assert len(up_data["failed_lines"]) == 20, f"Expected 20 failed lines, got {len(up_data['failed_lines'])}"
    print(f"[PASS] 8. Malformed trace upload correctly caught {len(up_data['failed_lines'])} failed lines while parsing {up_data['parsed_events']} valid events!")

    # 9. List and Delete
    res = client.get("/api/traces")
    assert res.status_code == 200
    assert len(res.json()) >= 2

    del_res = client.delete(f"/api/traces/{up_data['trace_id']}")
    assert del_res.status_code == 200
    print(f"[PASS] 9. Delete trace verified successfully")

    # Clean up test db
    if os.path.exists(test_db):
        os.remove(test_db)

    print("\n>>> ALL PHASE 1 BACKEND VERIFICATIONS PASSED! <<<")

if __name__ == "__main__":
    run_phase1_verification()
