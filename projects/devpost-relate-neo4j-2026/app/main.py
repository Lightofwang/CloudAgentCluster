"""
GraphLens - Main FastAPI Web Application & REST API.

Provides endpoints for:
- Health & Database Stats
- Document Ingestion, Retrieval & Deletion
- Interactive Graph Canvas & Neighbourhood Subgraphs
- Shortest Path Computations (Cypher shortestPath)
- Guarded Cypher Console with Destructive Statement Blocklist
- Graph-grounded Traceable Q&A (Ask)
- Agent Trace Recorder & Timeline
- Demo Data Seeding, Reset & Store Export
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, Query, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import relate

from app.ask import answer_question
from app.graph import get_db, RelateManager
from app.ingest import delete_document, ingest_document
from app.seed import reset_and_seed, seed_demo_data
from app.traces import get_trace_detail, list_traces, record_trace

app = FastAPI(
    title="GraphLens",
    description="Connected-Context Agent Memory Workbench powered by Relate embedded graph database",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# --- Request/Response Models ---

class DocumentIngestRequest(BaseModel):
    title: Optional[str] = "Untitled"
    text: str
    source: Optional[str] = "paste"


class CypherQueryRequest(BaseModel):
    cypher: str
    params: Optional[Dict[str, Any]] = None
    confirm: Optional[bool] = False


class AskRequest(BaseModel):
    question: str


class StepItem(BaseModel):
    name: str
    kind: Optional[str] = "tool"
    detail: Optional[str] = ""
    ts: Optional[str] = None
    entities: Optional[List[str]] = Field(default_factory=list)


class TraceCreateRequest(BaseModel):
    name: str
    steps: List[StepItem]


# --- 5.1 Health & Stats ---

@app.get("/api/health")
def get_health() -> Dict[str, Any]:
    db = get_db()
    relate_ver = getattr(relate, "__version__", "1.0.1")
    return {
        "status": "ok",
        "store": db.store_path,
        "relate": relate_ver,
    }


@app.get("/api/stats")
def get_stats() -> Dict[str, int]:
    db = get_db()
    try:
        docs = db.run_read("MATCH (d:Document) RETURN count(d) AS cnt")[0]["cnt"]
        chunks = db.run_read("MATCH (c:Chunk) RETURN count(c) AS cnt")[0]["cnt"]
        entities = db.run_read("MATCH (e:Entity) RETURN count(e) AS cnt")[0]["cnt"]
        relationships = db.run_read("MATCH ()-[r]->() RETURN count(r) AS cnt")[0]["cnt"]
        steps = db.run_read("MATCH (s:Step) RETURN count(s) AS cnt")[0]["cnt"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {
        "documents": docs,
        "chunks": chunks,
        "entities": entities,
        "relationships": relationships,
        "steps": steps,
    }


# --- 5.2 Documents ---

@app.post("/api/documents", status_code=status.HTTP_201_CREATED)
def post_document(req: DocumentIngestRequest) -> Dict[str, Any]:
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Document text cannot be empty.")
    db = get_db()
    try:
        res = ingest_document(
            db=db,
            title=req.title or "Untitled",
            text=req.text,
            source=req.source or "paste",
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.post("/api/documents/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)) -> Dict[str, Any]:
    filename = file.filename or "upload.txt"
    if not (filename.endswith(".txt") or filename.endswith(".md")):
        raise HTTPException(status_code=400, detail="Only .txt and .md files are allowed.")

    content = await file.read()
    if len(content) > 1_048_576:  # 1 MB limit
        raise HTTPException(status_code=400, detail="File size exceeds 1 MB limit.")

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8 text.")

    db = get_db()
    return ingest_document(
        db=db,
        title=filename,
        text=text,
        source=f"upload:{filename}",
    )


@app.get("/api/documents")
def list_documents() -> Dict[str, Any]:
    db = get_db()
    query = (
        "MATCH (d:Document) "
        "OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk) "
        "RETURN d.id AS id, d.title AS title, d.source AS source, "
        "       d.created_at AS created_at, count(c) AS chunk_count "
        "ORDER BY d.created_at DESC"
    )
    docs = db.run_read(query)
    return {"documents": docs}


@app.get("/api/documents/{doc_id}")
def get_document(doc_id: str) -> Dict[str, Any]:
    db = get_db()
    doc_res = db.run_read(
        "MATCH (d:Document {id: $id}) "
        "RETURN d.id AS id, d.title AS title, d.source AS source, "
        "       d.created_at AS created_at, d.text AS text",
        {"id": doc_id},
    )
    if not doc_res:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found.")

    doc = doc_res[0]
    chunks = db.run_read(
        "MATCH (d:Document {id: $id})-[:HAS_CHUNK]->(c:Chunk) "
        "RETURN c.id AS id, c.text AS text, c.position AS position "
        "ORDER BY c.position ASC",
        {"id": doc_id},
    )
    doc["chunks"] = chunks
    return doc


@app.delete("/api/documents/{doc_id}")
def delete_document_endpoint(doc_id: str) -> Dict[str, Any]:
    db = get_db()
    res = delete_document(db, doc_id)
    if not res.get("deleted"):
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found.")
    return res


# --- 5.3 Graph Queries & Cypher Console ---

@app.get("/api/graph")
def get_graph(
    limit: int = Query(default=200, ge=1, le=1000),
    labels: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    db = get_db()
    # Fetch Entity nodes
    label_filter = ""
    label_list = [l.strip() for l in labels.split(",") if l.strip()] if labels else []

    if label_list:
        nodes_query = (
            "MATCH (e:Entity) "
            "WHERE e.label IN $labels "
            "RETURN e.id AS id, elementId(e) AS element_id, e.label AS label, e.name AS name, properties(e) AS properties "
            "LIMIT $limit"
        )
        nodes_res = db.run_read(nodes_query, {"labels": label_list, "limit": limit})
    else:
        nodes_query = (
            "MATCH (e:Entity) "
            "RETURN e.id AS id, elementId(e) AS element_id, e.label AS label, e.name AS name, properties(e) AS properties "
            "LIMIT $limit"
        )
        nodes_res = db.run_read(nodes_query, {"limit": limit})

    node_ids = {n["id"] for n in nodes_res}
    node_names = {n["name"] for n in nodes_res}

    # Fetch edges between these nodes
    edges_query = (
        "MATCH (a:Entity)-[r]->(b:Entity) "
        "WHERE a.name IN $names AND b.name IN $names "
        "RETURN elementId(r) AS id, a.id AS from_id, a.name AS from_name, "
        "       b.id AS to_id, b.name AS to_name, type(r) AS type "
        "LIMIT 500"
    )
    edges_res = db.run_read(edges_query, {"names": list(node_names)})

    formatted_nodes = [
        {
            "id": n["id"],
            "element_id": n["element_id"],
            "label": n["label"],
            "name": n["name"],
            "properties": n.get("properties") or {},
        }
        for n in nodes_res
    ]

    formatted_edges = [
        {
            "id": e["id"],
            "from": e["from_id"],
            "from_name": e["from_name"],
            "to": e["to_id"],
            "to_name": e["to_name"],
            "type": e["type"],
        }
        for e in edges_res
    ]

    return {"nodes": formatted_nodes, "edges": formatted_edges}


@app.get("/api/graph/neighbors/{entity_id}")
def get_neighbors(entity_id: str, depth: int = Query(default=1, ge=1, le=2)) -> Dict[str, Any]:
    db = get_db()
    # Check if target entity exists
    match_ent = db.run_read(
        "MATCH (e:Entity) WHERE e.id = $id OR elementId(e) = $id OR e.name = $id "
        "RETURN e.id AS id, e.name AS name, e.label AS label, elementId(e) AS element_id, properties(e) AS properties",
        {"id": entity_id},
    )
    if not match_ent:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found.")

    center = match_ent[0]

    # Query 1-hop neighbours
    query = (
        "MATCH (center:Entity)-[r]-(neighbor:Entity) "
        "WHERE center.id = $id OR elementId(center) = $id OR center.name = $id "
        "RETURN center.id AS center_id, center.name AS center_name, center.label AS center_label, "
        "       elementId(center) AS center_eid, properties(center) AS center_props, "
        "       neighbor.id AS neighbor_id, neighbor.name AS neighbor_name, neighbor.label AS neighbor_label, "
        "       elementId(neighbor) AS neighbor_eid, properties(neighbor) AS neighbor_props, "
        "       elementId(r) AS edge_id, type(r) AS edge_type, "
        "       startNode(r) = center AS is_outgoing"
    )
    res = db.run_read(query, {"id": entity_id})

    nodes_map = {center["id"]: {
        "id": center["id"],
        "element_id": center["element_id"],
        "label": center["label"],
        "name": center["name"],
        "properties": center.get("properties") or {},
    }}
    edges = []

    for row in res:
        nid = row["neighbor_id"]
        if nid not in nodes_map:
            nodes_map[nid] = {
                "id": nid,
                "element_id": row["neighbor_eid"],
                "label": row["neighbor_label"],
                "name": row["neighbor_name"],
                "properties": row.get("neighbor_props") or {},
            }
        from_id = center["id"] if row["is_outgoing"] else nid
        to_id = nid if row["is_outgoing"] else center["id"]
        edges.append({
            "id": row["edge_id"],
            "from": from_id,
            "to": to_id,
            "type": row["edge_type"],
        })

    return {"nodes": list(nodes_map.values()), "edges": edges}


@app.get("/api/graph/path")
def get_shortest_path(from_id: str = Query(..., alias="from"), to_id: str = Query(..., alias="to")) -> Dict[str, Any]:
    db = get_db()
    if from_id == to_id:
        return {"path": [], "length": 0}

    # Verify both nodes exist
    n1 = db.run_read(
        "MATCH (a:Entity) WHERE a.id = $id OR elementId(a) = $id OR a.name = $id RETURN a.id AS id",
        {"id": from_id},
    )
    n2 = db.run_read(
        "MATCH (b:Entity) WHERE b.id = $id OR elementId(b) = $id OR b.name = $id RETURN b.id AS id",
        {"id": to_id},
    )
    if not n1 or not n2:
        raise HTTPException(status_code=404, detail="One or both entities not found.")

    cypher = (
        "MATCH (a:Entity), (b:Entity) "
        "WHERE (a.id = $from_id OR elementId(a) = $from_id OR a.name = $from_id) "
        "  AND (b.id = $to_id OR elementId(b) = $to_id OR b.name = $to_id) "
        "  AND a <> b "
        "MATCH p = shortestPath((a)-[*]-(b)) "
        "RETURN p"
    )
    try:
        res = db.execute(cypher, {"from_id": from_id, "to_id": to_id})
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"No path found: {str(e)}")

    rows = res.get("rows", [])
    if not rows or "p" not in rows[0]:
        raise HTTPException(status_code=404, detail=f"No path found between {from_id} and {to_id}.")

    path_data = rows[0]["p"]
    nodes = path_data.get("nodes", [])
    rels = path_data.get("relationships", [])

    path_steps = []
    for idx, r in enumerate(rels):
        u = nodes[idx]
        v = nodes[idx + 1]
        u_name = u.get("properties", {}).get("name") or str(u.get("id"))
        v_name = v.get("properties", {}).get("name") or str(v.get("id"))
        path_steps.append({
            "from": u_name,
            "to": v_name,
            "type": r.get("type", "RELATES_TO"),
        })

    return {
        "path": path_steps,
        "length": len(path_steps),
    }


@app.post("/api/graph/query")
def post_cypher_query(req: CypherQueryRequest) -> Dict[str, Any]:
    clean_cypher = req.cypher.strip()
    if not clean_cypher:
        raise HTTPException(status_code=400, detail="Cypher query cannot be empty.")

    db = get_db()
    if db.is_destructive(clean_cypher) and not req.confirm:
        raise HTTPException(
            status_code=400,
            detail="Destructive Cypher statement blocked (DROP / DETACH DELETE). Enable confirm toggle to execute.",
        )

    is_write = any(kw in clean_cypher.upper() for kw in ["CREATE", "MERGE", "SET", "DELETE", "REMOVE", "DROP"])

    try:
        res = db.execute(clean_cypher, params=req.params or {}, is_write=is_write)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cypher execution error: {str(e)}")


# --- 5.4 Ask (graph-grounded Q&A) ---

@app.post("/api/ask")
def post_ask(req: AskRequest) -> Dict[str, Any]:
    db = get_db()
    try:
        return answer_question(db, req.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ask evaluation failed: {str(e)}")


# --- 5.5 Traces ---

@app.post("/api/traces", status_code=status.HTTP_201_CREATED)
def post_trace(req: TraceCreateRequest) -> Dict[str, Any]:
    db = get_db()
    steps_payload = [s.model_dump() for s in req.steps]
    try:
        res = record_trace(db, name=req.name, steps=steps_payload)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record trace: {str(e)}")


@app.get("/api/traces")
def get_traces() -> Dict[str, Any]:
    db = get_db()
    traces = list_traces(db)
    return {"traces": traces}


@app.get("/api/traces/{trace_id}")
def get_trace(trace_id: str) -> Dict[str, Any]:
    db = get_db()
    trace = get_trace_detail(db, trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found.")
    return trace


# --- 5.6 Demo data & store management ---

@app.post("/api/demo/seed")
def post_demo_seed() -> Dict[str, Any]:
    db = get_db()
    try:
        return seed_demo_data(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Seeding demo data failed: {str(e)}")


@app.post("/api/demo/reset")
def post_demo_reset() -> Dict[str, Any]:
    db = get_db()
    try:
        return reset_and_seed(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resetting demo data failed: {str(e)}")


@app.get("/api/store/export")
def export_store():
    db = get_db()
    p = Path(db.store_path).resolve()
    if not p.exists() or p.stat().st_size == 0:
        raise HTTPException(status_code=404, detail="Store file does not exist yet. Seed or ingest data first.")
    return FileResponse(
        path=str(p),
        filename="graphlens.rl",
        media_type="application/octet-stream",
    )


# --- Frontend Static Files Mount ---

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
