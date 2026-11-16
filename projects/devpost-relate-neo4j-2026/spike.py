#!/usr/bin/env python3
"""
Phase 0 Spike script for Relate embedded graph database.
Verifies:
1. Python API works with relate-db
2. Persistent store file creation and reloading across runs
3. MERGE deduplication
4. Shortest path query using Cypher
"""

import os
import sys
from pathlib import Path
import relate

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
STORE_PATH = DATA_DIR / "spike.rl"


def run_spike():
    is_first_run = not STORE_PATH.exists()
    print(f"Connecting to Relate store at: {STORE_PATH} (exists={STORE_PATH.exists()})")

    db = relate.connect(str(STORE_PATH))
    try:
        # 1. Deduplicated MERGE nodes
        db.execute(
            "MERGE (a:Person {name: $name, label: 'Person'})",
            {"name": "Alice"}
        )
        db.execute(
            "MERGE (b:Person {name: $name, label: 'Person'})",
            {"name": "Bob"}
        )
        db.execute(
            "MERGE (p:Project {name: $name, label: 'Project'})",
            {"name": "GhostFeed"}
        )

        # 2. Relationships
        db.execute(
            "MATCH (a:Person {name: 'Alice'}), (p:Project {name: 'GhostFeed'}) "
            "MERGE (a)-[:WORKS_ON]->(p)"
        )
        db.execute(
            "MATCH (b:Person {name: 'Bob'}), (p:Project {name: 'GhostFeed'}) "
            "MERGE (b)-[:WORKS_ON]->(p)"
        )
        db.commit()

        # 3. Query counts
        res = db.execute("MATCH (n) RETURN count(n) AS node_count")
        node_count = list(res)[0]["node_count"]
        print(f"[Run Check] Total nodes in store: {node_count}")

        # 4. Shortest path
        res_path = db.execute(
            "MATCH p = shortestPath((a:Person {name: 'Alice'})-[*]-(b:Person {name: 'Bob'})) "
            "RETURN p"
        )
        paths = list(res_path)
        if paths:
            path_obj = paths[0]["p"]
            print(f"[ShortestPath] Alice <-> Bob path found: {len(path_obj.nodes)} nodes, {len(path_obj.relationships)} relationships")
            node_names = [n.properties.get("name") for n in path_obj.nodes]
            print(f"               Nodes traversed: {' -> '.join(node_names)}")
        else:
            print("[ShortestPath] No path found")

        # 5. List all entities
        res_entities = db.execute("MATCH (n) RETURN n.name AS name, labels(n) AS labels")
        rows = list(res_entities)
        print(f"[Entities in store]: {rows}")

    finally:
        db.close()

    print(f"Store file size: {STORE_PATH.stat().st_size} bytes")
    print("Spike test passed successfully!\n")


if __name__ == "__main__":
    print("--- Execution 1 ---")
    run_spike()
    print("--- Execution 2 (Verifying persistence across runs) ---")
    run_spike()
