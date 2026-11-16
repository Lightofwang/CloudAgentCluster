# GraphLens — Connected-Context Agent Memory Workbench

[![Relate Hackathon](https://img.shields.io/badge/Hackathon-Relate%20by%20Neo4j%202026-06b6d4)](https://relate.devpost.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-brightgreen.svg)](https://python.org)
[![Relate embedded](https://img.shields.io/badge/Relate%20DB-1.0.1%20Cypher%2025-orange.svg)](https://pypi.org/project/relate-db/)

> **Theme:** "Context, Connected" — AI agents that understand how your data connects.  
> GraphLens turns unstructured notes, documents, and agent execution traces into an interactive, queryable, and inspectable knowledge graph powered by **Relate** — Neo4j's open-source embedded graph database for AI agents (`pip install relate-db`, in-process, zero cloud infra, zero paid API keys).

---

## 1. How are you using Relate, and why?

### How we use Relate:
Relate is the **meaningful core** of GraphLens — every feature directly reads from and writes to the Relate embedded graph store (`./data/graphlens.rl`):
1. **Deduplicated Entity Merging (`MERGE`):** Ingested notes and documents are chunked and extracted into `(:Document)`, `(:Chunk)`, `(:Entity)` and `(:Step)` nodes with `[:HAS_CHUNK]`, `[:MENTIONS]`, `[:WORKS_ON]`, `[:USES]`, `[:RELATES_TO]`, `[:NEXT]`, and `[:TOUCHES]` edges using Cypher statements with transactional guarantees.
2. **Shortest-Path Navigation (`shortestPath`):** GraphLens utilizes Relate's embedded Cypher graph traversal algorithms (`shortestPath((a)-[*]-(b))`) to compute multi-hop relationships between people, projects, and concepts in under 5 milliseconds.
3. **Traceable Grounding for Agent Memory ("Ask" Q&A):** When an agent or user asks a question, GraphLens traverses the 1-hop and 2-hop neighbourhood in Relate, retrieves evidence paths, and cites exact graph paths with zero hallucinations.
4. **Live Cypher Console:** Users and judges can query the live embedded database using standard Cypher statements (`MATCH`, `RETURN`, `WHERE`, `ORDER BY`), with destructive statements (`DROP`, `DETACH DELETE`) safely guarded behind confirmation toggles.
5. **Agent Trace Graph:** Agent execution steps are recorded as linked `(:Step)-[:NEXT]->(:Step)` chains connected to the entities they accessed via `[:TOUCHES]`.

### Why Relate?
- **Zero Server Infrastructure:** Unlike server-based databases that require Docker containers, cloud clusters, or authentication tokens, Relate runs entirely in-process (`relate.connect()`).
- **Complete Offline Privacy:** No data ever leaves the local machine. Sensitive agent memories and personal notes remain 100% private.
- **Embedded Cypher 25 Engine:** Gives agents the full expressive power of declarative graph queries without external latency.
- **Transactional Portability:** The entire graph persists in a single file (`./data/graphlens.rl`), exportable with one click and inspectable using the official `relate` CLI.

---

## 2. Architecture & Data Model

```cypher
(:Document {id, title, source, created_at, text})
(:Chunk    {id, text, position, doc_id})
(:Entity   {id, name, label})           // label ∈ Person | Project | Topic | Tool | Date
(:Trace    {id, name, created_at})
(:Step     {id, name, kind, detail, ts, position, trace_id})

(:Document)-[:HAS_CHUNK]->(:Chunk)
(:Chunk)-[:MENTIONS]->(:Entity)
(:Entity)-[:WORKS_ON | USES | RELATES_TO]->(:Entity)
(:Trace)-[:HAS_STEP]->(:Step)
(:Step)-[:NEXT]->(:Step)
(:Step)-[:TOUCHES]->(:Entity)
```

---

## 3. Quick Start (Run Locally in < 60s)

### Prerequisites
- Python 3.11+
- No API keys needed! 100% local and offline.

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/Lightofwang/CloudAgentCluster.git
cd CloudAgentCluster/projects/devpost-relate-neo4j-2026

# Install dependencies
pip install -r requirements.txt
```

### 2. Start the Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open your browser at **`http://localhost:8000`**.

---

## 4. Demo Walkthrough (≤ 2 Minutes)

1. **(0:00 - Load Demo Data):** Click the **"⚡ Load Demo Data"** button in the top navbar. In under 1 second, Relate seeds 12 documents, 61 entities, and 250+ relationships across People, Projects, Tools, Topics, and Dates. The force-directed graph canvas comes alive.
2. **(0:20 - Node Inspection):** Click the **"GhostFeed"** or **"Alice"** node. The right inspector panel reveals its degree, properties, and 1-hop connected entities with direction indicators.
3. **(0:40 - Graph-Grounded Q&A):** Switch to the **"Ask"** tab on the left and submit *"What is Alice working on?"*. GraphLens retrieves the connected context and outputs:
   > *"Alice works on AgentMem and GhostFeed."*
   along with inline citations (`[Person:Alice] -WORKS_ON-> [Project:GhostFeed]`) and a collapsible *"Why this answer?"* panel showing the exact Cypher query and evidence chunks.
4. **(1:00 - Cypher Console):** Click the bottom Cypher console strip and run:
   ```cypher
   MATCH (p:Person)-[:WORKS_ON]->(j:Project) RETURN p.name AS person, j.name AS project
   ```
   The result renders in an interactive table with sub-millisecond execution time.
5. **(1:20 - Real-Time Ingest):** In the Ingest tab, paste a new note:
   > *"Sarah leads NeoFlow using Python and Docker."*  
   Click **"Extract & Ingest Note"**. Watch the new nodes and relationships appear live on the canvas.
6. **(1:40 - Export & Inspect Store):** Click **"💾 Export .rl"** in the top navbar to download the persistent store file. Judges can open and query it using Relate's native tools.

---

## 5. REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check, store file path, and Relate version |
| `GET` | `/api/stats` | Graph counts: documents, chunks, entities, relations, steps |
| `POST` | `/api/documents` | Ingest plain text note with entity/relationship extraction |
| `POST` | `/api/documents/upload` | Ingest `.txt` / `.md` file (< 1MB) |
| `GET` | `/api/documents` | List all ingested documents |
| `GET` | `/api/documents/{id}` | Get document text and sentence chunks |
| `DELETE` | `/api/documents/{id}` | Delete document, chunks, and orphan entities |
| `GET` | `/api/graph` | Subgraph for canvas visualization (supports `limit`, `labels`) |
| `GET` | `/api/graph/neighbors/{id}` | 1-hop neighbourhood of an entity |
| `GET` | `/api/graph/path?from={id}&to={id}` | Shortest path between two entities via Cypher |
| `POST` | `/api/graph/query` | Run arbitrary Cypher queries (destructive calls guarded) |
| `POST` | `/api/ask` | Graph-grounded question answering with citations |
| `POST` | `/api/traces` | Record agent execution step trace |
| `GET` | `/api/traces` | List all recorded agent traces |
| `GET` | `/api/traces/{id}` | Get trace steps and touched entities |
| `POST` | `/api/demo/seed` | Seed 12 demo documents and 1 demo trace |
| `POST` | `/api/demo/reset` | Wipe graph and re-seed clean dataset |
| `GET` | `/api/store/export` | Download the raw `.rl` database file |

---

## 6. Running Automated Tests

Run the full test suite with `unittest`:

```bash
python -m unittest discover -s tests -v
```

Expected output:
```
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
Ran 21 tests in 1.70s

OK
```

---

## 7. License

MIT License. See [LICENSE](LICENSE) for details.
