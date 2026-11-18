import json
import os
import sqlite3
import unittest
import uuid

from app.db import (
    batch_insert_anomalies,
    batch_insert_events,
    get_connection,
    init_db,
    save_trace_metadata
)
from app.rules import (
    PRIORITY_INVERSION_THRESHOLD_NS,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM
)
from app.services.anomalies import detect_anomalies

class TestAnomalyRulesEngine(unittest.TestCase):
    def setUp(self):
        self.test_db = f"/tmp/test_anomalies_{uuid.uuid4().hex[:8]}.db"
        self.conn = sqlite3.connect(self.test_db)
        self.conn.row_factory = sqlite3.Row
        init_db(self.test_db)

    def tearDown(self):
        self.conn.close()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def _create_trace(self, trace_id: str, events: list):
        start_ns = min(e["timestamp_ns"] for e in events) if events else 0
        end_ns = max(e["timestamp_ns"] for e in events) if events else 0
        save_trace_metadata(self.conn, {
            "trace_id": trace_id,
            "filename": f"{trace_id}.trace.jsonl",
            "total_lines": len(events),
            "parsed_events": len(events),
            "failed_lines": [],
            "time_range": {"start_ns": start_ns, "end_ns": end_ns},
            "threads": 4,
            "created_at": "2026-11-18T00:00:00Z"
        })
        batch_insert_events(self.conn, trace_id, events)

    def test_clean_trace_has_zero_anomalies(self):
        # Normal periodic scheduling without any anomalies
        events = []
        for i in range(10):
            t = i * 50_000_000
            events.append({
                "timestamp_ns": t,
                "event_class": "thread-state",
                "thread_id": 1,
                "thread_name": "clean-task",
                "process": "clean-proc",
                "old_state": "READY",
                "new_state": "RUNNING",
                "cpu": 0
            })
            events.append({
                "timestamp_ns": t + 5_000_000,
                "event_class": "thread-state",
                "thread_id": 1,
                "thread_name": "clean-task",
                "process": "clean-proc",
                "old_state": "RUNNING",
                "new_state": "READY",
                "cpu": 0
            })
        self._create_trace("tr_clean", events)
        anomalies = detect_anomalies(self.conn, "tr_clean")
        self.assertEqual(len(anomalies), 0, f"Expected 0 anomalies on clean trace, got {len(anomalies)}")

    def test_priority_inversion_minimal_reproduction(self):
        # Low prio thread holds mutex; high prio thread blocked for 200ms (> 100ms threshold)
        events = [
            # High prio thread starts running
            {
                "timestamp_ns": 1_000_000_000,
                "event_class": "thread-state",
                "thread_id": 10,
                "thread_name": "high-prio-task",
                "process": "control-svc",
                "old_state": "READY",
                "new_state": "RUNNING",
                "cpu": 0,
                "priority": 60
            },
            # High prio thread attempts mutex and blocks on low-prio holder
            {
                "timestamp_ns": 1_020_000_000,
                "event_class": "thread-state",
                "thread_id": 10,
                "thread_name": "high-prio-task",
                "process": "control-svc",
                "old_state": "RUNNING",
                "new_state": "BLOCKED",
                "cpu": 0,
                "priority": 60,
                "holder_thread": "low-prio-logger",
                "holder_tid": 20
            },
            # 200ms later, low-prio unlocks and high prio resumes
            {
                "timestamp_ns": 1_220_000_000,
                "event_class": "thread-state",
                "thread_id": 10,
                "thread_name": "high-prio-task",
                "process": "control-svc",
                "old_state": "BLOCKED",
                "new_state": "READY",
                "cpu": 0,
                "priority": 60
            }
        ]
        self._create_trace("tr_pi", events)
        anomalies = detect_anomalies(self.conn, "tr_pi")

        self.assertEqual(len(anomalies), 1)
        an = anomalies[0]
        self.assertEqual(an["type"], "priority-inversion")
        self.assertEqual(an["severity"], SEVERITY_HIGH)
        self.assertIn("high-prio-task", an["threads"])
        self.assertIn("low-prio-logger", an["threads"])
        self.assertEqual(an["start_ns"], 1_020_000_000)
        self.assertEqual(an["end_ns"], 1_220_000_000)
        self.assertIn("200ms", an["description"])
        self.assertIn("优先级继承", an["suggestion"])

    def test_deadline_miss_minimal_reproduction(self):
        # slog2 warning for deadline miss
        events = [
            {
                "timestamp_ns": 2_000_000_000,
                "event_class": "slog2",
                "thread_id": 2,
                "thread_name": "motor-loop",
                "process": "motor-ctrl",
                "severity": "warn",
                "message": "Periodic execution interval exceeded deadline (actual: 80ms, expected: 20ms)"
            }
        ]
        self._create_trace("tr_dl", events)
        anomalies = detect_anomalies(self.conn, "tr_dl")

        self.assertEqual(len(anomalies), 1)
        an = anomalies[0]
        self.assertEqual(an["type"], "deadline-miss")
        self.assertEqual(an["severity"], SEVERITY_HIGH)
        self.assertIn("motor-loop", an["threads"])
        self.assertIn("周期执行超时错失截止期", an["description"])

    def test_interrupt_storm_minimal_reproduction(self):
        # 550 interrupts on IRQ 33 within 600ms (< 1 second)
        events = []
        start_t = 3_000_000_000
        for i in range(550):
            events.append({
                "timestamp_ns": start_t + (i * 1_000_000),  # 1ms apart = 550ms total
                "event_class": "interrupt",
                "irq": 33,
                "entry_exit": "entry",
                "cpu": 1,
                "duration_ns": 5000
            })
        self._create_trace("tr_irq", events)
        anomalies = detect_anomalies(self.conn, "tr_irq")

        self.assertEqual(len(anomalies), 1)
        an = anomalies[0]
        self.assertEqual(an["type"], "interrupt-storm")
        self.assertEqual(an["severity"], SEVERITY_CRITICAL)
        self.assertIn("IRQ-33", an["threads"])
        self.assertIn("超过安全阈值", an["description"])

    def test_message_queue_backlog_minimal_reproduction(self):
        # Channel backlog reaching 25 messages (> 20 threshold)
        events = []
        base_t = 4_000_000_000
        for i in range(25):
            events.append({
                "timestamp_ns": base_t + (i * 2_000_000),
                "event_class": "ipc-message",
                "channel_id": 909,
                "channel_name": "chan-control",
                "sender_tid": 1,
                "receiver_tid": 2,
                "msg_type": "send",
                "pending_queue_size": i + 1
            })
        self._create_trace("tr_bk", events)
        anomalies = detect_anomalies(self.conn, "tr_bk")

        self.assertEqual(len(anomalies), 1)
        an = anomalies[0]
        self.assertEqual(an["type"], "message-queue-backlog")
        self.assertEqual(an["severity"], SEVERITY_MEDIUM)
        self.assertIn("chan-control", an["threads"])
        self.assertIn("堆积 25 条未处理消息", an["description"])

if __name__ == "__main__":
    unittest.main()
