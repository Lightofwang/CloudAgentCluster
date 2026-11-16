"""
Tests for Graph-grounded Ask Engine.
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

from app.ask import answer_question
from app.graph import RelateManager
from app.seed import seed_demo_data


class TestAsk(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_ask.rl")
        self.db = RelateManager(self.db_path)
        seed_demo_data(self.db)

    def tearDown(self):
        self.db.close()
        self.tmp_dir.cleanup()

    def test_ask_alice_working_on(self):
        res = answer_question(self.db, "What is Alice working on?")
        answer = res["answer"]
        citations = res["citations"]
        cypher = res["cypher_used"]

        self.assertTrue("GhostFeed" in answer or "AgentMem" in answer)
        self.assertGreaterEqual(len(citations), 1)
        self.assertIn("Alice", citations[0]["path"])
        self.assertIn("MATCH", cypher)

    def test_ask_tools_used_by_bob(self):
        res = answer_question(self.db, "What tools does Bob use?")
        answer = res["answer"]
        citations = res["citations"]

        self.assertTrue(any(tool in answer for tool in ["SQLite", "Python", "FastAPI", "Relate"]))
        self.assertGreaterEqual(len(citations), 1)

    def test_ask_unrelated_honest_fallback(self):
        res = answer_question(self.db, "How do black holes collide in the cosmos?")
        answer = res["answer"]
        citations = res["citations"]

        self.assertIn("couldn't find", answer.lower())
        self.assertEqual(len(citations), 0)

    def test_empty_question(self):
        res = answer_question(self.db, "   ")
        self.assertEqual(res["answer"], "Please ask a question.")
        self.assertEqual(res["citations"], [])


if __name__ == "__main__":
    unittest.main()
