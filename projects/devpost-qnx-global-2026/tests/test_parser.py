import io
import json
import unittest

from app.qnx_trace import (
    QnxTraceParseError,
    parse_line,
    stream_parse_trace_lines,
    validate_and_normalize_event
)

class TestQnxTraceParser(unittest.TestCase):
    def test_parse_thread_state_valid(self):
        line = json.dumps({
            "timestamp_ns": 123456789,
            "event_class": "thread-state",
            "thread_id": 3,
            "thread_name": "sensor-fusion",
            "process": "fusion-svc",
            "old_state": "READY",
            "new_state": "RUNNING",
            "cpu": 1,
            "priority": 60
        })
        ev = parse_line(line, 1)
        self.assertEqual(ev["event_class"], "thread-state")
        self.assertEqual(ev["thread_id"], 3)
        self.assertEqual(ev["thread_name"], "sensor-fusion")
        self.assertEqual(ev["old_state"], "READY")
        self.assertEqual(ev["new_state"], "RUNNING")
        self.assertEqual(ev["priority"], 60)

    def test_parse_kernel_call_valid(self):
        line = json.dumps({
            "timestamp_ns": 200000000,
            "event_class": "kernel-call",
            "thread_id": 2,
            "thread_name": "motor-loop",
            "process": "motor-ctrl",
            "call_name": "MsgSendv",
            "entry_exit": "entry",
            "cpu": 0
        })
        ev = parse_line(line, 2)
        self.assertEqual(ev["event_class"], "kernel-call")
        self.assertEqual(ev["call_name"], "MsgSendv")
        self.assertEqual(ev["entry_exit"], "entry")

    def test_parse_interrupt_valid(self):
        line = json.dumps({
            "timestamp_ns": 300000000,
            "event_class": "interrupt",
            "irq": 42,
            "entry_exit": "entry",
            "cpu": 1,
            "duration_ns": 12000
        })
        ev = parse_line(line, 3)
        self.assertEqual(ev["event_class"], "interrupt")
        self.assertEqual(ev["irq"], 42)
        self.assertEqual(ev["duration_ns"], 12000)

    def test_parse_ipc_message_valid(self):
        line = json.dumps({
            "timestamp_ns": 400000000,
            "event_class": "ipc-message",
            "channel_id": 105,
            "channel_name": "chan-telemetry",
            "sender_tid": 1,
            "receiver_tid": 5,
            "msg_type": "send",
            "msg_size": 128,
            "roundtrip_ns": 500000
        })
        ev = parse_line(line, 4)
        self.assertEqual(ev["event_class"], "ipc-message")
        self.assertEqual(ev["channel_id"], 105)
        self.assertEqual(ev["msg_type"], "send")
        self.assertEqual(ev["roundtrip_ns"], 500000)

    def test_parse_pulse_valid(self):
        line = json.dumps({
            "timestamp_ns": 500000000,
            "event_class": "pulse",
            "channel_id": 102,
            "code": 42,
            "value": 99
        })
        ev = parse_line(line, 5)
        self.assertEqual(ev["event_class"], "pulse")
        self.assertEqual(ev["code"], 42)
        self.assertEqual(ev["value"], 99)

    def test_parse_slog2_json_and_text(self):
        # JSON slog2
        json_line = json.dumps({
            "timestamp_ns": 600000000,
            "event_class": "slog2",
            "process": "fusion-svc",
            "severity": "warn",
            "message": "Packet loss detected"
        })
        ev1 = parse_line(json_line, 6)
        self.assertEqual(ev1["event_class"], "slog2")
        self.assertEqual(ev1["severity"], "warn")

        # Text slog2
        text_line = "[slog2] 700000000 [INFO] disk-logger[6]: Sync buffer flushed"
        ev2 = parse_line(text_line, 7)
        self.assertEqual(ev2["event_class"], "slog2")
        self.assertEqual(ev2["timestamp_ns"], 700000000)
        self.assertEqual(ev2["process"], "disk-logger")
        self.assertEqual(ev2["thread_id"], 6)
        self.assertEqual(ev2["message"], "Sync buffer flushed")

    def test_parse_error_handling(self):
        # Invalid JSON
        with self.assertRaises(QnxTraceParseError):
            parse_line("bad json {", 1)

        # Missing timestamp
        with self.assertRaises(QnxTraceParseError):
            parse_line(json.dumps({"event_class": "thread-state"}), 2)

        # Unknown event class
        with self.assertRaises(QnxTraceParseError):
            parse_line(json.dumps({"timestamp_ns": 100, "event_class": "unknown-foo"}), 3)

        # Invalid thread state
        with self.assertRaises(QnxTraceParseError):
            parse_line(json.dumps({
                "timestamp_ns": 100,
                "event_class": "thread-state",
                "thread_id": 1,
                "old_state": "INVALID",
                "new_state": "RUNNING"
            }), 4)

    def test_streaming_parse_with_failures(self):
        lines = [
            json.dumps({"timestamp_ns": 100, "event_class": "interrupt", "irq": 10}),
            "corrupted line #1",
            json.dumps({"timestamp_ns": 200, "event_class": "interrupt", "irq": 10}),
            "{bad json",
            json.dumps({"timestamp_ns": 300, "event_class": "interrupt", "irq": 10}),
        ]
        stream = io.StringIO("\n".join(lines))
        parser_gen = stream_parse_trace_lines(stream, batch_size=2)

        all_batches = []
        stats = None
        while True:
            try:
                batch, _ = next(parser_gen)
                all_batches.extend(batch)
            except StopIteration as stop:
                stats = stop.value
                break

        self.assertEqual(len(all_batches), 3)
        self.assertEqual(stats["total_lines"], 5)
        self.assertEqual(stats["parsed_events"], 3)
        self.assertEqual(len(stats["failed_lines"]), 2)
        self.assertEqual(stats["failed_lines"][0]["line"], 2)
        self.assertEqual(stats["failed_lines"][1]["line"], 4)

    def test_streaming_large_dataset_performance(self):
        # Stream 10,000 events
        def line_generator():
            for i in range(10_000):
                yield json.dumps({
                    "timestamp_ns": i * 1_000_000,
                    "event_class": "thread-state",
                    "thread_id": (i % 8) + 1,
                    "thread_name": f"th-{(i % 8) + 1}",
                    "process": "proc-test",
                    "old_state": "READY",
                    "new_state": "RUNNING",
                    "cpu": i % 2
                })

        parser_gen = stream_parse_trace_lines(line_generator(), batch_size=2500)
        total_parsed = 0
        batch_count = 0
        stats = None
        while True:
            try:
                batch, _ = next(parser_gen)
                batch_count += 1
                total_parsed += len(batch)
            except StopIteration as stop:
                stats = stop.value
                break

        self.assertEqual(total_parsed, 10_000)
        self.assertEqual(batch_count, 4)
        self.assertEqual(stats["parsed_events"], 10_000)
        self.assertEqual(len(stats["failed_lines"]), 0)

if __name__ == "__main__":
    unittest.main()
