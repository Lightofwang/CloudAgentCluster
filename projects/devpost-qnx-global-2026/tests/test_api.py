import json
import os
import unittest
import uuid

from fastapi.testclient import TestClient
from main import app
from app.db import init_db

class TestTraceLensApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db = f"/tmp/test_api_{uuid.uuid4().hex[:8]}.db"
        os.environ["TRACELENS_DB_PATH"] = cls.test_db
        init_db(cls.test_db)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)

    def test_01_health_and_reference(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok"})

        res = self.client.get("/api/reference/event-types")
        self.assertEqual(res.status_code, 200)
        self.assertIn("event_classes", res.json())
        classes = [c["name"] for c in res.json()["event_classes"]]
        self.assertIn("thread-state", classes)
        self.assertIn("kernel-call", classes)
        self.assertIn("interrupt", classes)
        self.assertIn("ipc-message", classes)
        self.assertIn("pulse", classes)
        self.assertIn("slog2", classes)

    def test_02_generate_trace(self):
        payload = {
            "threads": 6,
            "duration_seconds": 5,
            "inject": ["priority-inversion", "deadline-miss"]
        }
        res = self.client.post("/api/traces/generate", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["trace_id"].startswith("tr_"))
        self.assertGreater(data["parsed_events"], 100)
        self.assertEqual(len(data["failed_lines"]), 0)
        self.assertGreaterEqual(data["threads"], 6)

        # Store trace_id for subsequent tests
        TestTraceLensApi.generated_trace_id = data["trace_id"]

    def test_03_get_trace_by_id(self):
        tid = TestTraceLensApi.generated_trace_id
        res = self.client.get(f"/api/traces/{tid}")
        self.assertEqual(res.status_code, 200)
        meta = res.json()
        self.assertEqual(meta["trace_id"], tid)
        self.assertIn("time_range", meta)

    def test_04_get_trace_not_found(self):
        res = self.client.get("/api/traces/non_existent_trace_id")
        self.assertEqual(res.status_code, 404)
        self.assertIn("detail", res.json())

    def test_05_events_pagination_and_filtering(self):
        tid = TestTraceLensApi.generated_trace_id

        # Paginated fetch
        res = self.client.get(f"/api/traces/{tid}/events?limit=25&offset=0")
        self.assertEqual(res.status_code, 200)
        p1 = res.json()
        self.assertEqual(len(p1["events"]), 25)
        self.assertGreater(p1["total"], 25)

        # Filter by event_class
        res = self.client.get(f"/api/traces/{tid}/events?event_class=interrupt&limit=50")
        self.assertEqual(res.status_code, 200)
        irq_page = res.json()
        for ev in irq_page["events"]:
            self.assertEqual(ev["event_class"], "interrupt")

        # Filter by thread_id
        res = self.client.get(f"/api/traces/{tid}/events?thread_id=1&limit=50")
        self.assertEqual(res.status_code, 200)
        th1_page = res.json()
        for ev in th1_page["events"]:
            self.assertEqual(ev["thread_id"], 1)

    def test_06_timeline_endpoint(self):
        tid = TestTraceLensApi.generated_trace_id
        res = self.client.get(f"/api/traces/{tid}/timeline")
        self.assertEqual(res.status_code, 200)
        tl = res.json()
        self.assertIn("threads", tl)
        self.assertIn("interrupts", tl)
        self.assertGreater(len(tl["threads"]), 0)

        # Verify segment structure
        first_th = tl["threads"][0]
        self.assertIn("thread_id", first_th)
        self.assertIn("segments", first_th)
        if first_th["segments"]:
            seg = first_th["segments"][0]
            self.assertIn("start_ns", seg)
            self.assertIn("end_ns", seg)
            self.assertIn("state", seg)
            self.assertIn(seg["state"], ["RUNNING", "READY", "BLOCKED"])

    def test_07_stats_endpoint(self):
        tid = TestTraceLensApi.generated_trace_id
        res = self.client.get(f"/api/traces/{tid}/stats")
        self.assertEqual(res.status_code, 200)
        stats = res.json()
        self.assertIn("cpu", stats)
        self.assertIn("ipc", stats)
        self.assertIn("interrupts", stats)
        self.assertGreater(len(stats["cpu"]), 0)
        self.assertIn("running_pct", stats["cpu"][0])

    def test_08_anomalies_endpoint(self):
        tid = TestTraceLensApi.generated_trace_id
        res = self.client.get(f"/api/traces/{tid}/anomalies")
        self.assertEqual(res.status_code, 200)
        anomalies = res.json()
        self.assertIsInstance(anomalies, list)
        self.assertGreater(len(anomalies), 0)
        types = [a["type"] for a in anomalies]
        self.assertIn("priority-inversion", types)

    def test_09_upload_trace_with_malformed_lines(self):
        content = "\n".join([
            json.dumps({"timestamp_ns": 100, "event_class": "interrupt", "irq": 10}),
            "corrupted line 1",
            json.dumps({"timestamp_ns": 200, "event_class": "interrupt", "irq": 10}),
            "corrupted line 2",
            json.dumps({"timestamp_ns": 300, "event_class": "interrupt", "irq": 10})
        ])
        files = {"file": ("test_upload.trace.jsonl", content.encode("utf-8"), "application/x-jsonlines")}
        res = self.client.post("/api/traces/upload", files=files)
        self.assertEqual(res.status_code, 200)
        up = res.json()
        self.assertEqual(up["total_lines"], 5)
        self.assertEqual(up["parsed_events"], 3)
        self.assertEqual(len(up["failed_lines"]), 2)

        # Clean up this uploaded trace
        del_res = self.client.delete(f"/api/traces/{up['trace_id']}")
        self.assertEqual(del_res.status_code, 200)

    def test_10_delete_trace(self):
        tid = TestTraceLensApi.generated_trace_id
        res = self.client.delete(f"/api/traces/{tid}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "deleted", "trace_id": tid})

        # Verify subsequent query returns 404
        get_res = self.client.get(f"/api/traces/{tid}")
        self.assertEqual(get_res.status_code, 404)

if __name__ == "__main__":
    unittest.main()
