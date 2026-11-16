# GraphLens — Connected-Context Agent Memory Workbench

## 1. Project Overview

**Hackathon:** Relate by Neo4j Hackathon 2026 (Devpost, https://relate.devpost.com/)
**Theme:** "Context, Connected" — agents that understand how your data connects.
**Project:** GraphLens is a local-first, demo-ready full-stack web application that turns a
pile of unstructured notes, documents, and agent traces into a queryable knowledge graph
powered by **Relate** — Neo4j's open-source embedded graph database for AI agents
(`pip install relate-db`, in-process, no server, no signup, no paid API key).

The core insight: an AI agent is only as good as the context it can reach. GraphLens
ingests plain-text notes, extracts entities and relationships with a transparent,
rule-based extractor (zero paid LLM calls), stores them as a Cypher property graph in a
single persistent Relate store (`./data/graphlens.rl`), and lets the user explore and
query that graph through (a) an interactive force-directed graph canvas, (b) a Cypher
console, and (c) a graph-grounded "Ask" mode that answers questions by traversing the
graph and citing the exact paths it used — every answer is traceable to nodes and
relationships a judge can inspect.

**Why it wins this hackathon:** it uses Relate as the *meaningful core* of the product
(every feature reads/writes the graph), it is honest about what is local vs. cloud
(everything runs locally), it ships a persistent Relate store judges can open with the
`relate` CLI, and it is demoable in under 2 minutes.

## 2. Core Features

### 2.1 Ingest (Notes → Graph)
- Paste text or upload `.txt` / `.md` files; each document becomes a `Document` node.
- Rule-based extractor (regex + keyword gazetteer + sentence co-occurrence) pulls out
  `Person`, `Project`, `Topic`, `Tool`, `Date` entities and `MENTIONS` / `RELATES_TO` /
  `WORKS_ON` / `USES` relationships. No external API, fully deterministic, fully testable.
- Chunking: documents split into `Chunk` nodes (max ~800 chars, sentence-aligned),
  linked `(:Document)-[:HAS_CHUNK]->(:Chunk)`, chunks `MENTIONS` entities.
- Duplicate detection: same (label, name) entity is merged (`MERGE`), never duplicated.

### 2.2 Graph Explorer (interactive canvas)
- Force-directed rendering of the graph (canvas, custom lightweight layout — no CDN
  dependency so the demo works offline).
- Click a node → side panel shows properties, degree, 1-hop neighbourhood, and all
  relationships with their types.
- Filter by label, search by name, highlight paths between two selected nodes
  (shortest path via Cypher `shortestPath`).

### 2.3 Cypher Console
- Run arbitrary read/write Cypher against the live Relate store; results as a table
  plus JSON. Guarded: destructive statements (`DETACH DELETE`, `DROP`) require an
  explicit confirm toggle and are logged.
- Built-in example queries (one click): "all people and their projects",
  "topics connected to two projects", "orphan entities with no relationships".

### 2.4 Ask — graph-grounded Q&A (local, no paid LLM)
- Question → keyword/entity extraction → Cypher neighbourhood retrieval (up to 2 hops)
  → ranked evidence paths → a composed answer built from retrieved facts with inline
  citations (`[Person:Alice] -WORKS_ON-> [Project:GhostFeed]`).
- TF-IDF ranking over chunks for fallback text evidence when no graph path matches.
- Every answer ships a "Why this answer" panel listing the Cypher query run, the
  nodes/edges used, and the scores — full traceability, no black box.

### 2.5 Agent Trace Recorder
- A tiny HTTP endpoint (`POST /api/traces`) records agent steps as
  `(:Step)-[:NEXT]->(:Step)` chains linked to the entities they touched, so an agent
  run becomes a navigable graph. The UI renders a trace as a timeline + mini-graph.
- Seeded demo trace included so judges see it without running an agent.

### 2.6 Persistence & Portability
- Single persistent store file `./data/graphlens.rl` (Relate transactional filesystem
  store). "Export store" button downloads the `.rl` file; judges can open it with
  `relate query --database ./graphlens.rl`.
- One-click "Load demo dataset" seeds ~12 documents, ~40 entities, ~70 relationships.
- "Reset demo data" wipes and reseeds.

## 3. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.11+ / FastAPI + Uvicorn | Fast, typed, auto OpenAPI docs |
| Graph DB | Relate (`relate-db` PyPI, embedded, Cypher 25) | Hackathon product; in-process, zero infra |
| Frontend | Vanilla HTML/CSS/JS, single page, canvas graph | Zero build step, works offline, fast demo |
| Tests | Python `unittest` (stdlib) + FastAPI `TestClient` | No extra deps; `python -m unittest discover` |
| Storage | `./data/graphlens.rl` (Relate store) + JSON seed files | Portable, inspectable |
| Config | `.env` (optional) — `GRAPH_STORE_PATH`, `PORT` | No secrets required |

Zero paid API keys are required to run locally. Everything works offline after
`pip install -r requirements.txt`.

## 4. Data Model (Relate / Cypher)

```cypher
(:Document {id, title, source, created_at})
(:Chunk    {id, text, position})
(:Entity   {id, name, label})          // label ∈ Person | Project | Topic | Tool | Date
(:Step     {id, name, kind, detail, ts})
(:Document)-[:HAS_CHUNK]->(:Chunk)
(:Chunk)-[:MENTIONS]->(:Entity)
(:Entity)-[:WORKS_ON | USES | RELATES_TO]->(:Entity)
(:Step)-[:NEXT]->(:Step)
(:Step)-[:TOUCHES]->(:Entity)
```

Entity identity: `MERGE (e:Entity {name: $name, label: $label})` — name+label unique.

## 5. REST API Endpoints & JSON Schemas

Base URL: `http://localhost:8000`. All responses JSON. Errors: `{ "detail": "..." }`
with standard HTTP codes (400 validation, 404 not found, 500 server).

### 5.1 Health & Stats
- `GET /api/health` → `200 { "status": "ok", "store": "./data/graphlens.rl", "relate": "1.x" }`
- `GET /api/stats` → `200 { "documents": 12, "chunks": 48, "entities": 41, "relationships": 73, "steps": 9 }`

### 5.2 Documents
- `POST /api/documents` — ingest one document.
  Request: `{ "title": "Kiroween notes", "text": "...", "source": "paste" }`
  Response: `201 { "document_id": "doc_01", "chunks_created": 5, "entities_found": 9, "relationships_created": 12 }`
- `GET /api/documents` → `200 { "documents": [{ "id", "title", "source", "created_at", "chunk_count" }] }`
- `GET /api/documents/{id}` → document + its chunks.
- `DELETE /api/documents/{id}` → `200 { "deleted": true, "nodes_removed": n }` (removes
  document, chunks, and orphan entities).

### 5.3 Graph
- `GET /api/graph?limit=200&labels=Person,Project` → full graph for the canvas:
  `200 { "nodes": [{ "id", "label", "name", "properties": {} }], "edges": [{ "id", "from", "to", "type" }] }`
- `GET /api/graph/neighbors/{entity_id}?depth=1` → 1-hop neighbourhood subgraph.
- `GET /api/graph/path?from=<id>&to=<id>` → `200 { "path": [{ "from","to","type" }], "length": 3 }`
  (404 if no path).
- `POST /api/graph/query` — Cypher console.
  Request: `{ "cypher": "MATCH (p:Entity) RETURN p.name LIMIT 5", "params": {} }`
  Response: `200 { "columns": ["p.name"], "rows": [[...]], "stats": {...}, "elapsed_ms": 3 }`

### 5.4 Ask (graph-grounded Q&A)
- `POST /api/ask` — Request: `{ "question": "What is Alice working on?" }`
  Response: `200 { "answer": "Alice works on GhostFeed and LocalScribe. [citations]", "citations": [{ "path": "Alice -WORKS_ON-> GhostFeed", "score": 0.92 }], "cypher_used": "MATCH ...", "evidence_chunks": [{ "text": "...", "score": 0.81 }] }`

### 5.5 Traces
- `POST /api/traces` — Request: `{ "name": "nightly-digest", "steps": [{ "name": "fetch feeds", "kind": "tool", "detail": "...", "entities": ["Hacker News"] }] }`
  Response: `201 { "trace_id": "tr_01", "steps_created": 4 }`
- `GET /api/traces` → list of traces with step counts.
- `GET /api/traces/{id}` → trace steps in order + touched entities.

### 5.6 Demo data & store
- `POST /api/demo/seed` → `200 { "documents": 12, "entities": 41, "relationships": 73 }`
- `POST /api/demo/reset` → wipes store and reseeds.
- `GET /api/store/export` → downloads the `graphlens.rl` store file.

## 6. Frontend UI Layout

Single-page app (`frontend/index.html` + `app.js` + `styles.css`), no build step.

```
┌──────────────────────────────────────────────────────────────┐
│ Header: GraphLens logo · store status badge · [Load demo]    │
│         [Reset] [Export .rl] · stats strip (docs/entities/…) │
├──────────┬───────────────────────────────────┬───────────────┤
│ Left     │  Graph canvas (force-directed)    │ Right panel:  │
│ panel:   │  - drag nodes, zoom, pan          │ node detail / │
│ - Ingest │  - click node → highlight 1-hop   │ Ask answer +  │
│   (paste │  - path mode: pick two nodes      │ citations /   │
│   /file) │  - legend of labels & edge types  │ Cypher result │
│ - Search │                                   │ table         │
│ - Ask box│  Bottom strip: Cypher console     │               │
│ - Traces │  (query input + example chips)    │               │
└──────────┴───────────────────────────────────┴───────────────┘
```

- **Ingest tab:** textarea + file input + "Ingest" button; shows extraction result
  (entities/relationships created) inline.
- **Ask tab:** question input, answer card with citations, "Why this answer" expander.
- **Traces tab:** trace list, timeline view, mini-graph of steps.
- Visual language: dark graph canvas, amber/cyan node palette per label, monospace
  Cypher console, responsive down to 900px width.

## 7. Non-Functional Constraints

- **Local-first:** runs fully offline after install; no paid API keys, no accounts.
- **Startup:** `pip install -r requirements.txt && uvicorn app.main:app` → usable in
  < 60 s; demo seed loads in < 5 s.
- **Determinism:** same seed data → same graph, same Ask answers (fixed ranking).
- **Persistence:** Relate store survives restarts; exportable `.rl` file judges can open
  with the official CLI.
- **Test coverage:** `unittest` suite covers extractor, graph CRUD, every API endpoint,
  Ask ranking, and trace recording; `python -m unittest discover -s tests -v` green.
- **Hackathon compliance:** project started during the contest period; public GitHub
  repo tagged with topic `relate` (+ `relate-neo4j-hackathon`); README answers
  "how are you using Relate, and why?"; 1–2 min demo video; MIT license.
- **Safety:** Cypher console blocks `DROP`/`DETACH DELETE` without confirm toggle;
  file upload limited to `.txt`/`.md`, max 1 MB; no user data leaves the machine.

## 8. Demo Script (≤ 2 minutes)

1. (0:00) Load demo data — graph canvas fills with people, projects, topics.
2. (0:20) Click "GhostFeed" node — panel shows its neighbours and relationships.
3. (0:40) Ask "What is Alice working on?" — answer appears with cited graph paths.
4. (1:00) Cypher console: run `MATCH (p:Entity)-[:WORKS_ON]->(j) RETURN p.name, j.name`.
5. (1:20) Paste a new note → watch entities/edges appear live on the canvas.
6. (1:40) Export `.rl` store; show it opening in the `relate` CLI.
