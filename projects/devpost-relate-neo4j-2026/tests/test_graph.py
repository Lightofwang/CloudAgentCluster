"""
Tests for Graph Manager, Ingestion, Deduplication, and Shortest Path.
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
from app.ingest import delete_document, ingest_document
from app.seed import seed_demo_data


class TestGraph(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_graph.rl")
        self.db = RelateManager(self.db_path)

    def tearDown(self):
        self.db.close()
        self.tmp_dir.cleanup()

    def test_merge_dedup_across_ingests(self):
        # Ingest document 1
        res1 = ingest_document(
            self.db,
            title="Note 1",
            text="Alice works on GhostFeed using Python.",
            source="test",
            doc_id="doc_01",
        )
        self.assertGreaterEqual(res1["entities_found"], 3)

        # Ingest document 2 containing same entities
        res2 = ingest_document(
            self.db,
            title="Note 2",
            text="Alice works on GhostFeed using Python.",
            source="test",
            doc_id="doc_02",
        )

        # Verify entity count in store is not duplicated
        res_alice = self.db.run_read("MATCH (e:Entity {name: 'Alice'}) RETURN count(e) AS cnt")
        self.assertEqual(res_alice[0]["cnt"], 1)

        res_prjs = self.db.run_read("MATCH (p:Project {name: 'GhostFeed'}) RETURN count(p) AS cnt")
        self.assertEqual(res_prjs[0]["cnt"], 1)

    def test_delete_document_removes_chunks_and_orphans(self):
        # Ingest a standalone document with unique orphan entity
        text = "Zoe works on OmniGraph using Vue."
        res = ingest_document(self.db, title="Zoe Note", text=text, doc_id="doc_zoe")
        self.assertEqual(res["document_id"], "doc_zoe")

        # Verify Zoe exists
        zoe_before = self.db.run_read("MATCH (e:Entity {name: 'Zoe'}) RETURN count(e) AS cnt")[0]["cnt"]
        self.assertEqual(zoe_before, 1)

        # Delete document
        del_res = delete_document(self.db, "doc_zoe")
        self.assertTrue(del_res["deleted"])

        # Document should be gone
        doc_cnt = self.db.run_read("MATCH (d:Document {id: 'doc_zoe'}) RETURN count(d) AS cnt")[0]["cnt"]
        self.assertEqual(doc_cnt, 0)

        # Chunks should be gone
        chk_cnt = self.db.run_read("MATCH (c:Chunk {doc_id: 'doc_zoe'}) RETURN count(c) AS cnt")[0]["cnt"]
        self.assertEqual(chk_cnt, 0)

    def test_shortest_path_on_seed_graph(self):
        # Populate with demo data
        seed_demo_data(self.db)

        # Find shortest path between Alice and Bob
        cypher = (
            "MATCH (a:Entity {name: 'Alice'}), (b:Entity {name: 'Bob'}) "
            "WHERE a <> b "
            "MATCH p = shortestPath((a)-[*]-(b)) "
            "RETURN p"
        )
        res = self.db.execute(cypher)
        rows = res["rows"]
        self.assertGreater(len(rows), 0)
        path_obj = rows[0]["p"]
        nodes = path_obj["nodes"]
        self.assertGreaterEqual(len(nodes), 2)
        names = [n["properties"]["name"] for n in nodes]
        self.assertEqual(names[0], "Alice")
        self.assertEqual(names[-1], "Bob")


if __name__ == "__main__":
    unittest.main()
