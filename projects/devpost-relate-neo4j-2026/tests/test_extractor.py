"""
Tests for Entity & Relationship Extractor.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.extractor import (
    extract_document,
    extract_entities,
    extract_relationships,
    split_into_sentences,
)


class TestExtractor(unittest.TestCase):
    def test_split_into_sentences(self):
        text = "Alice works on GhostFeed. Bob leads LocalScribe! Does Carol research Neo4j?"
        sentences = split_into_sentences(text)
        self.assertEqual(len(sentences), 3)
        self.assertIn("Alice works on GhostFeed.", sentences[0])

    def test_empty_and_whitespace_text(self):
        self.assertEqual(split_into_sentences(""), [])
        self.assertEqual(split_into_sentences("   \n\n  "), [])
        doc = extract_document("")
        self.assertEqual(doc["entities"], [])
        self.assertEqual(doc["relationships"], [])
        self.assertEqual(doc["sentences"], [])

    def test_entity_extraction_types(self):
        sentence = "Alice is building GhostFeed using Python and Relate on 2026-12-11."
        entities = extract_entities(sentence)
        entity_map = {e["name"]: e["label"] for e in entities}

        self.assertIn("Alice", entity_map)
        self.assertEqual(entity_map["Alice"], "Person")

        self.assertIn("GhostFeed", entity_map)
        self.assertEqual(entity_map["GhostFeed"], "Project")

        self.assertIn("Python", entity_map)
        self.assertEqual(entity_map["Python"], "Tool")

        self.assertIn("Relate", entity_map)
        self.assertEqual(entity_map["Relate"], "Tool")

        self.assertIn("2026-12-11", entity_map)
        self.assertEqual(entity_map["2026-12-11"], "Date")

    def test_relationship_extraction_cues(self):
        sentence = "Alice works on GhostFeed using Python and FastAPI."
        entities = extract_entities(sentence)
        rels = extract_relationships(sentence, entities)

        rel_tuples = {(r["from"], r["to"], r["type"]) for r in rels}

        # Works on
        self.assertIn(("Alice", "GhostFeed", "WORKS_ON"), rel_tuples)
        # Uses
        self.assertIn(("Alice", "Python", "USES"), rel_tuples)
        self.assertIn(("GhostFeed", "Python", "USES"), rel_tuples)

    def test_determinism(self):
        text = (
            "Carol researches Graph Database architectures using Relate. "
            "She is evaluating Cypher queries and Connected-Context."
        )
        res1 = extract_document(text)
        res2 = extract_document(text)

        self.assertEqual(res1["entities"], res2["entities"])
        self.assertEqual(res1["relationships"], res2["relationships"])


if __name__ == "__main__":
    unittest.main()
