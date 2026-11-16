# GraphLens — Implementation Plan

**Hackathon:** Relate by Neo4j Hackathon 2026 — deadline **2026-12-11 18:00 PST**
(2026-12-12 10:00 CST). **Project:** GraphLens, a connected-context agent memory
workbench. **Stack:** Python 3.11+ / FastAPI + Relate (`relate-db`, embedded Cypher 25)
+ vanilla HTML/CSS/JS frontend. **Zero paid API keys.**

Total build budget: ~4–5 focused days for one solo developer. Each phase ends with a
runnable, verifiable checkpoint.

## Phase 0 — Setup & Relate Spike (0.5 day)

1. Create public GitHub repo `graphlens`, add topics `relate` and
   `relate-neo4j-hackathon`, MIT license, README skeleton answering
   "how are you using Relate, and why?".
2. `python -m venv .venv && pip install fastapi uvicorn relate-db python-multipart`.
3. Spike script `spike.py`: `import relate; db = relate.connect("./data/spike.rl")`,
   run `CREATE` / `MATCH` / `shortestPath` Cypher; confirm: Python API works on this
   machine, persistent store file is created, `MERGE` dedup behaves as expected.
4. Pin the working `relate-db` version in `requirements.txt`.
5. **Checkpoint:** spike prints rows from a persistent store across two runs.

## Phase 1 — Backend (2 days)

### 1.1 Project skeleton
- Layout:
  ```
  graphlens/
  ├── app/
  │   ├── main.py          # FastAPI app, CORS, static mount, routers
  │   ├── graph.py         # Relate connection + Cypher helpers (single writer lock)
  │   ├── extractor.py     # rule-based entity/relation extraction
  │   ├── ingest.py        # chunking + MERGE writes
  │   ├── ask.py           # question → retrieval → cited answer
  │   ├── traces.py        # trace recording helpers
  │   └── seed.py          # demo dataset (12 docs)
  ├── frontend/
  │   ├── index.html  app.js  styles.css
  ├── tests/
  │   ├── test_extractor.py  test_graph.py  test_api.py  test_ask.py  test_traces.py
  ├── data/  (gitignored except .gitkeep; store file lives here)
  ├── requirements.txt  README.md  LICENSE
  ```
- `graph.py`: one `relate.connect(store_path)` instance, a `threading.Lock` around
  writes (Relate is single-user per process), helpers `run(cypher, params)`,
  `run_read`, `run_write`; translate Relate rows to plain dicts.

### 1.2 Data model & ingest
- Implement the model from `spec.md` §4: `Document`, `Chunk`, `Entity`, `Step` nodes
  and `HAS_CHUNK`, `MENTIONS`, `WORKS_ON`, `USES`, `RELATES_TO`, `NEXT`, `TOUCHES`.
- `extractor.py`: sentence splitter; entity patterns —
  `Person` (capitalised name gazetteer + `X works on / built / leads`), `Project`
  (CamelCase / quoted names), `Topic` (keyword list: RSS, agents, graph, …),
  `Tool` (known tools list), `Date` (ISO / "Dec 11" patterns); co-occurrence in one
  sentence ⇒ `RELATES_TO`; verb cues ⇒ `WORKS_ON` / `USES`.
- `ingest.py`: chunk text at sentence boundaries (~800 chars), `MERGE` entities,
  create relationships, return counts.
- Endpoints: `POST /api/documents`, `GET /api/documents`, `GET /api/documents/{id}`,
  `DELETE /api/documents/{id}`, `GET /api/health`, `GET /api/stats`.
- **Checkpoint:** `curl` ingest of a sample note returns counts; stats endpoint
  reflects the new nodes; store file persists after restart.

### 1.3 Graph query endpoints
- `GET /api/graph` (label filter, limit), `GET /api/graph/neighbors/{id}`,
  `GET /api/graph/path` (Cypher `shortestPath`), `POST /api/graph/query`
  (console; blocklist `DROP` / `DETACH DELETE` unless `confirm=true`).
- **Checkpoint:** seed → `/api/graph` returns nodes/edges the frontend can draw;
  path endpoint returns a 2–3 hop path between two seeded entities.

### 1.4 Ask (graph-grounded Q&A)
- `ask.py`: extract entity mentions from the question (same extractor) → Cypher
  neighbourhood query (≤2 hops) → score paths (edge-type weight × TF-IDF chunk
  score) → compose answer sentences from the top facts with inline citations →
  return `{answer, citations, cypher_used, evidence_chunks}`.
- Fallback: pure TF-IDF chunk retrieval when no entity matches; honest
  "I couldn't find that in your graph" when nothing scores above threshold.
- Endpoint `POST /api/ask`.
- **Checkpoint:** "What is Alice working on?" returns a cited answer from seed data;
  an unrelated question returns the honest fallback.

### 1.5 Traces
- `POST /api/traces`, `GET /api/traces`, `GET /api/traces/{id}`; steps stored as a
  `NEXT` chain with `TOUCHES` edges to entities; seed one demo trace.
- **Checkpoint:** posting a 4-step trace renders as an ordered chain via the API.

### 1.6 Demo data & store management
- `seed.py`: 12 realistic documents (hackathon notes, project ideas, reading lists)
  producing ~40 entities / ~70 relationships; one demo trace.
- `POST /api/demo/seed`, `POST /api/demo/reset`, `GET /api/store/export`
  (streams the `.rl` file).
- **Checkpoint:** fresh clone → install → seed → all stats match expected counts.

## Phase 2 — Frontend (1.5 days)

### 2.1 Shell & layout
- `index.html`: header (logo, store badge, stats strip, Load demo / Reset / Export
  buttons), left panel (Ingest / Ask / Traces tabs), centre canvas, right detail
  panel, bottom Cypher console. `styles.css`: dark theme, amber/cyan label palette,
  monospace console. No CDN dependencies — fully offline.

### 2.2 Graph canvas (`app.js`, ~600 lines)
- Fetch `/api/graph`; force-directed layout (simple spring simulation, requestAnimationFrame).
- Interactions: drag node, wheel zoom, pan, click node → highlight 1-hop + fill right
  panel; label filter checkboxes; "Path mode": click two nodes → call
  `/api/graph/path` and highlight the path; search box focuses a node by name.
- Render: circles sized by degree, labels on hover/zoom, edge-type legend.

### 2.3 Panels
- **Ingest:** textarea + file input (`.txt`/`.md`, ≤1 MB) → `POST /api/documents` →
  show created counts, then refresh canvas.
- **Ask:** input + button → `POST /api/ask` → answer card with citations and a
  "Why this answer" expander (Cypher used + evidence scores).
- **Traces:** list → click → timeline + mini-graph of steps.
- **Cypher console:** input, example-query chips, results table + JSON view,
  confirm toggle for destructive statements.
- **Checkpoint:** full manual walkthrough of the demo script (spec.md §8) works
  end-to-end in the browser with zero console errors.

## Phase 3 — Automated Tests & Verification (1 day)

### 3.1 Test suite (`python -m unittest discover -s tests -v`)
- `test_extractor.py`: known sentences → expected entities/relations; no false
  positives on empty text; determinism (same input → same output).
- `test_graph.py`: MERGE dedup (ingest same doc twice → one entity); delete
  document removes chunks + orphans; shortest path correctness on seed graph.
- `test_api.py` (FastAPI `TestClient`, temp store per test): every endpoint —
  happy path + 400/404 cases; console blocklist; export returns a file.
- `test_ask.py`: seeded questions return cited answers; unknown topic returns
  honest fallback; citations reference real node IDs.
- `test_traces.py`: trace creation order, `TOUCHES` edges, list/detail endpoints.
- Target: all green, no network calls in tests (use a temp `./data/test_*.rl` store,
  cleaned up in `tearDown`).

### 3.2 Verification checklist
- [ ] Fresh clone → `pip install -r requirements.txt` → `uvicorn app.main:app`
      → `http://localhost:8000` loads, health `ok`, seed loads < 5 s.
- [ ] Demo script (spec.md §8) runs in ≤ 2 min, recorded as the submission video.
- [ ] `relate query --database ./data/graphlens.rl "MATCH (n) RETURN count(n)"`
      returns the same counts as `/api/stats`.
- [ ] Repo is public, tagged `relate`, README answers "how/why Relate", MIT license.
- [ ] Devpost submission: title, description, repo link, 1–2 min video, screenshots.
- [ ] `python -m unittest discover -s tests -v` → all tests pass (record output).

### 3.3 Submission
- Record the 1–2 min demo video (screen share, no login required to view).
- Submit on Devpost before **2026-12-11 18:00 PST**; verify the repo tag `relate`
  is present and the store export opens in the CLI.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Relate is new/experimental; Python API gaps | Phase 0 spike first; fall back to the `relate` CLI via subprocess or the HTTP surface if a binding call is missing |
| Rule-based extractor misses entities | Gazetteer + patterns tuned on seed data; Ask falls back to TF-IDF chunks, so recall degrades gracefully |
| Single-writer embedded DB under concurrent requests | One connection + write lock; reads are fast; demo load is single-user |
| Canvas performance with large graphs | Cap `/api/graph` at 200 nodes by default; label filters; pagination by neighbourhood |
