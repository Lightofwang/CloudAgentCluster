"""
Comprehensive Tests for GraphLens REST API Endpoints.
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

from fastapi.testclient import TestClient
from app.graph import get_db, reset_db_instance
from app.main import app


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_api.rl")
        # Point the global DB to temporary file
        reset_db_instance()
        self.db = get_db(self.db_path)
        self.client = TestClient(app)

    def tearDown(self):
        reset_db_instance()
        self.tmp_dir.cleanup()

    def test_health_endpoint(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("relate", data)
        self.assertIn("store", data)

    def test_stats_endpoint_empty_and_seeded(self):
        # Empty
        r = self.client.get("/api/stats")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["documents"], 0)

        # Seed
        r_seed = self.client.post("/api/demo/seed")
        self.assertEqual(r_seed.status_code, 200)
        seed_data = r_seed.json()
        self.assertEqual(seed_data["documents"], 12)

        # Stats after seed
        r_stats = self.client.get("/api/stats")
        self.assertEqual(r_stats.status_code, 200)
        self.assertEqual(r_stats.json()["documents"], 12)
        self.assertGreater(r_stats.json()["entities"], 30)

    def test_document_ingest_get_and_delete(self):
        # Ingest document
        payload = {
            "title": "API Test Note",
            "text": "Alice is working on FastTree using Python and Docker.",
            "source": "paste",
        }
        r_post = self.client.post("/api/documents", json=payload)
        self.assertEqual(r_post.status_code, 201)
        doc_data = r_post.json()
        doc_id = doc_data["document_id"]
        self.assertIn("doc_", doc_id)

        # Bad request: empty text
        r_bad = self.client.post("/api/documents", json={"title": "Empty", "text": "   "})
        self.assertEqual(r_bad.status_code, 400)

        # List documents
        r_list = self.client.get("/api/documents")
        self.assertEqual(r_list.status_code, 200)
        docs = r_list.json()["documents"]
        self.assertTrue(any(d["id"] == doc_id for d in docs))

        # Get single document
        r_get = self.client.get(f"/api/documents/{doc_id}")
        self.assertEqual(r_get.status_code, 200)
        self.assertEqual(r_get.json()["title"], "API Test Note")
        self.assertGreaterEqual(len(r_get.json()["chunks"]), 1)

        # Get non-existent document
        r_missing = self.client.get("/api/documents/non_existent_id")
        self.assertEqual(r_missing.status_code, 404)

        # Delete document
        r_del = self.client.delete(f"/api/documents/{doc_id}")
        self.assertEqual(r_del.status_code, 200)
        self.assertTrue(r_del.json()["deleted"])

        # Delete again -> 404
        r_del_again = self.client.delete(f"/api/documents/{doc_id}")
        self.assertEqual(r_del_again.status_code, 404)

    def test_document_file_upload(self):
        content = b"Bob leads DataSync with SQLite."
        files = {"file": ("test_upload.md", content, "text/markdown")}
        r = self.client.post("/api/documents/upload", files=files)
        self.assertEqual(r.status_code, 201)
        self.assertIn("document_id", r.json())

        # Invalid extension
        bad_files = {"file": ("test_upload.pdf", b"bad", "application/pdf")}
        r_bad = self.client.post("/api/documents/upload", files=bad_files)
        self.assertEqual(r_bad.status_code, 400)

    def test_graph_and_path_endpoints(self):
        # Seed
        self.client.post("/api/demo/seed")

        # Get full graph
        r_graph = self.client.get("/api/graph?limit=100")
        self.assertEqual(r_graph.status_code, 200)
        nodes = r_graph.json()["nodes"]
        edges = r_graph.json()["edges"]
        self.assertGreater(len(nodes), 0)
        self.assertGreater(len(edges), 0)

        # Filter by label
        r_filter = self.client.get("/api/graph?labels=Person,Project")
        self.assertEqual(r_filter.status_code, 200)
        filtered_labels = {n["label"] for n in r_filter.json()["nodes"]}
        self.assertTrue(filtered_labels.issubset({"Person", "Project"}))

        # Shortest path between Alice and Bob
        r_path = self.client.get("/api/graph/path?from=Alice&to=Bob")
        self.assertEqual(r_path.status_code, 200)
        path_data = r_path.json()
        self.assertIn("path", path_data)
        self.assertGreaterEqual(path_data["length"], 1)

        # Shortest path between same node
        r_same = self.client.get("/api/graph/path?from=Alice&to=Alice")
        self.assertEqual(r_same.status_code, 200)
        self.assertEqual(r_same.json()["length"], 0)

        # Shortest path non-existent node
        r_none = self.client.get("/api/graph/path?from=UnknownNodeA&to=UnknownNodeB")
        self.assertEqual(r_none.status_code, 404)

        # 1-hop neighbours
        r_neigh = self.client.get("/api/graph/neighbors/Alice")
        self.assertEqual(r_neigh.status_code, 200)
        self.assertGreaterEqual(len(r_neigh.json()["nodes"]), 2)

    def test_cypher_console_and_destructive_blocklist(self):
        self.client.post("/api/demo/seed")

        # Valid read query
        r_query = self.client.post(
            "/api/graph/query",
            json={"cypher": "MATCH (p:Person) RETURN p.name AS name LIMIT 3"},
        )
        self.assertEqual(r_query.status_code, 200)
        self.assertIn("columns", r_query.json())
        self.assertIn("rows", r_query.json())
        self.assertEqual(len(r_query.json()["rows"]), 3)

        # Destructive statement without confirm -> 400
        r_blocked = self.client.post(
            "/api/graph/query",
            json={"cypher": "MATCH (n) DETACH DELETE n", "confirm": False},
        )
        self.assertEqual(r_blocked.status_code, 400)
        self.assertIn("Destructive Cypher statement blocked", r_blocked.json()["detail"])

        # Destructive statement WITH confirm -> 200
        r_allowed = self.client.post(
            "/api/graph/query",
            json={"cypher": "MATCH (n) DETACH DELETE n", "confirm": True},
        )
        self.assertEqual(r_allowed.status_code, 200)

        # Verify all nodes deleted
        r_check = self.client.get("/api/stats")
        self.assertEqual(r_check.json()["entities"], 0)

    def test_store_export(self):
        # Populate store
        self.client.post("/api/demo/seed")

        # Export store
        r_export = self.client.get("/api/store/export")
        self.assertEqual(r_export.status_code, 200)
        self.assertEqual(r_export.headers.get("content-type"), "application/octet-stream")
        self.assertGreater(len(r_export.content), 0)


if __name__ == "__main__":
    unittest.main()
