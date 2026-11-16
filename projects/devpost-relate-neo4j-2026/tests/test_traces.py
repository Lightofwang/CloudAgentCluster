"""
Tests for Agent Trace Recorder.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.graph import RelateManager
from app.traces import get_trace_detail, list_traces, record_trace


class TestTraces(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_traces.rl")
        self.db = RelateManager(self.db_path)

    def tearDown(self):
        self.db.close()
        self.tmp_dir.cleanup()

    def test_record_and_query_trace(self):
        steps = [
            {"name": "Scan Feeds", "kind": "tool", "detail": "Read RSS feeds", "entities": ["RSS"]},
            {"name": "Analyze", "kind": "plan", "detail": "Formulate query", "entities": ["Relate"]},
            {"name": "Synthesize", "kind": "action", "detail": "Create digest", "entities": ["Context"]},
        ]
        res = record_trace(self.db, name="Daily Digest Agent", steps=steps, trace_id="tr_test_01")
        self.assertEqual(res["trace_id"], "tr_test_01")
        self.assertEqual(res["steps_created"], 3)

        # List traces
        traces = list_traces(self.db)
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0]["name"], "Daily Digest Agent")
        self.assertEqual(traces[0]["step_count"], 3)

        # Check detail and step order
        detail = get_trace_detail(self.db, "tr_test_01")
        self.assertIsNotNone(detail)
        self.assertEqual(len(detail["steps"]), 3)
        self.assertEqual(detail["steps"][0]["name"], "Scan Feeds")
        self.assertEqual(detail["steps"][1]["name"], "Analyze")
        self.assertEqual(detail["steps"][2]["name"], "Synthesize")

        # Verify NEXT chain
        next_edges = self.db.run_read("MATCH (s1:Step)-[:NEXT]->(s2:Step) RETURN s1.name AS s1, s2.name AS s2")
        self.assertEqual(len(next_edges), 2)
        self.assertEqual(next_edges[0]["s1"], "Scan Feeds")
        self.assertEqual(next_edges[0]["s2"], "Analyze")

        # Verify TOUCHES edges
        touches = self.db.run_read("MATCH (s:Step)-[:TOUCHES]->(e:Entity) RETURN s.name AS step, e.name AS entity")
        self.assertEqual(len(touches), 3)

    def test_get_non_existent_trace(self):
        detail = get_trace_detail(self.db, "non_existent_trace_id")
        self.assertIsNone(detail)


if __name__ == "__main__":
    unittest.main()
