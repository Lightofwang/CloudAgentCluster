# GraphLens — Implementation Results

**Project:** Relate by Neo4j Hackathon 2026: GraphLens — Connected-Context Agent Memory Workbench  
**Hub Entry Slug:** `devpost-relate-neo4j-2026`  
**Date:** 2026-11-16  
**Status:** Completed & Fully Verified  

---

## 1. What Was Built

GraphLens is a local-first, full-stack connected-context agent memory workbench powered by **Relate** (`relate-db` 1.0.1, openCypher 25 embedded graph engine).

### Core Components Implemented:
1. **Embedded Graph Database Core (`app/graph.py`):**
   - Thread-isolated `RelateManager` managing the single-process, thread-affine Relate engine via a dedicated background task queue.
   - Support for transactional reads and writes, Cypher query timing (`elapsed_ms`), and serialization of nodes, relationships, and paths into clean JSON.
   - Built-in guardrails blocking destructive statements (`DROP`, `DETACH DELETE`) unless an explicit confirmation toggle is enabled.
2. **Rule-Based Entity & Relationship Extractor (`app/extractor.py`):**
   - 100% offline, zero-paid-API deterministic extractor with zero cloud dependencies.
   - Extracts 5 entity categories: `Person`, `Project`, `Topic`, `Tool`, `Date`.
   - Extracts 3 core relationship types: `WORKS_ON` (Person ➔ Project), `USES` (Entity ➔ Tool), `RELATES_TO` (Co-occurrence / Semantic link).
3. **Document Ingestion & Merging (`app/ingest.py`):**
   - Sentence-aligned chunking (~800 chars max) creating `(:Document)-[:HAS_CHUNK]->(:Chunk)`.
   - Chunks linked to mentioned entities via `[:MENTIONS]`.
   - Deduplicated entity merging using Cypher `MERGE (e:Entity {name: $name, label: $label}) ON CREATE SET e.id = $id`.
   - Clean document deletion removing documents, chunks, and orphan nodes.
4. **Graph-Grounded Q&A Engine (`app/ask.py`):**
   - Zero-hallucination, traceable answering engine.
   - Traverses 1-hop and 2-hop graph neighbourhoods in Relate and computes TF-IDF scores over sentence chunks.
   - Synthesizes grounded answers with inline path citations (`[Person:Alice] -WORKS_ON-> [Project:GhostFeed]`).
   - Honest fallback when context is absent ("I couldn't find any connected context about that in your graph.").
5. **Agent Trace Recorder (`app/traces.py`):**
   - Records agent reasoning and execution sequences as `(:Trace)-[:HAS_STEP]->(:Step)-[:NEXT]->(:Step)` chains linked to touched entities via `[:TOUCHES]`.
6. **Realistic Demo Seed Dataset (`app/seed.py`):**
   - 12 comprehensive documents and 1 demo trace (`nightly-digest-agent`) producing 61 entities and 256 relationships.
   - Instant 1-click load and reset capabilities.
7. **Full REST API (`app/main.py`):**
   - Complete FastAPI application with endpoints for health, stats, documents, graph subgraphs, shortest path (`shortestPath`), Cypher console, Ask, traces, and `.rl` store export.
8. **Interactive Vanilla Frontend (`frontend/`):**
   - Dark-themed single-page application with zero CDN / third-party dependencies (100% offline capable).
   - High-DPI HTML5 canvas with a custom force-directed spring physics engine.
   - Interactive node dragging, panning, zooming, 1-hop neighbourhood highlighting, path mode between any two selected nodes, real-time Cypher console with preset query chips, and context inspector.

---

## 2. How to Run

### Install Dependencies
```bash
cd projects/devpost-relate-neo4j-2026
pip install -r requirements.txt
```

### Start Server
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Open **`http://localhost:8000`** in your browser.

---

## 3. Test Results

### Test Suite Execution
Run from the repository root:
```bash
python -m unittest discover -s projects/devpost-relate-neo4j-2026/tests -p "test_*.py" -v
```

Or from the project directory:
```bash
cd projects/devpost-relate-neo4j-2026
python -m unittest discover -s tests -v
```

### Test Output (100% Passed):
```text
test_cypher_console_and_destructive_blocklist (test_api.TestAPI.test_cypher_console_and_destructive_blocklist) ... ok
test_document_file_upload (test_api.TestAPI.test_document_file_upload) ... ok
test_document_ingest_get_and_delete (test_api.TestAPI.test_document_ingest_get_and_delete) ... ok
test_graph_and_path_endpoints (test_api.TestAPI.test_graph_and_path_endpoints) ... ok
test_health_endpoint (test_api.TestAPI.test_health_endpoint) ... ok
test_stats_endpoint_empty_and_seeded (test_api.TestAPI.test_stats_endpoint_empty_and_seeded) ... ok
test_store_export (test_api.TestAPI.test_store_export) ... ok
test_ask_alice_working_on (test_ask.TestAsk.test_ask_alice_working_on) ... ok
test_ask_tools_used_by_bob (test_ask.TestAsk.test_ask_tools_used_by_bob) ... ok
test_ask_unrelated_honest_fallback (test_ask.TestAsk.test_ask_unrelated_honest_fallback) ... ok
test_empty_question (test_ask.TestAsk.test_empty_question) ... ok
test_determinism (test_extractor.TestExtractor.test_determinism) ... ok
test_empty_and_whitespace_text (test_extractor.TestExtractor.test_empty_and_whitespace_text) ... ok
test_entity_extraction_types (test_extractor.TestExtractor.test_entity_extraction_types) ... ok
test_relationship_extraction_cues (test_extractor.TestExtractor.test_relationship_extraction_cues) ... ok
test_split_into_sentences (test_extractor.TestExtractor.test_split_into_sentences) ... ok
test_delete_document_removes_chunks_and_orphans (test_graph.TestGraph.test_delete_document_removes_chunks_and_orphans) ... ok
test_merge_dedup_across_ingests (test_graph.TestGraph.test_merge_dedup_across_ingests) ... ok
test_shortest_path_on_seed_graph (test_graph.TestGraph.test_shortest_path_on_seed_graph) ... ok
test_get_non_existent_trace (test_traces.TestTraces.test_get_non_existent_trace) ... ok
test_record_and_query_trace (test_traces.TestTraces.test_record_and_query_trace) ... ok

----------------------------------------------------------------------
Ran 21 tests in 1.702s

OK
```

All 21 unit and end-to-end integration tests passed without errors.
