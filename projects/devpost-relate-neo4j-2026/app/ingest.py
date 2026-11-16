"""
GraphLens - Document Ingestion & Graph Merging.

Chunks documents, extracts entities and relationships, and writes
(:Document), (:Chunk), (:Entity), and (:Step) graphs to Relate.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any, Dict, List, Optional

from app.extractor import extract_document
from app.graph import RelateManager


def chunk_text(sentences: List[Dict[str, Any]], max_chars: int = 800) -> List[Dict[str, Any]]:
    """
    Group sentences into chunks of max ~800 characters while preserving sentence boundaries.
    """
    if not sentences:
        return []

    chunks: List[Dict[str, Any]] = []
    current_sentences: List[str] = []
    current_entities: List[Dict[str, str]] = []
    current_length = 0

    for s in sentences:
        s_text = s["text"]
        s_len = len(s_text)
        if current_sentences and (current_length + s_len > max_chars):
            # Finish current chunk
            chunk_txt = " ".join(current_sentences)
            # Dedup chunk entities
            seen_e = set()
            chunk_ents = []
            for e in current_entities:
                k = (e["label"], e["name"].lower())
                if k not in seen_e:
                    seen_e.add(k)
                    chunk_ents.append(e)
            chunks.append({
                "position": len(chunks),
                "text": chunk_txt,
                "entities": chunk_ents,
            })
            current_sentences = []
            current_entities = []
            current_length = 0

        current_sentences.append(s_text)
        current_entities.extend(s.get("entities", []))
        current_length += s_len + 1

    if current_sentences:
        chunk_txt = " ".join(current_sentences)
        seen_e = set()
        chunk_ents = []
        for e in current_entities:
            k = (e["label"], e["name"].lower())
            if k not in seen_e:
                seen_e.add(k)
                chunk_ents.append(e)
        chunks.append({
            "position": len(chunks),
            "text": chunk_txt,
            "entities": chunk_ents,
        })

    return chunks


def ingest_document(
    db: RelateManager,
    title: str,
    text: str,
    source: str = "paste",
    doc_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ingest a document: creates Document, Chunks, Entities, and Relationships in Relate.
    """
    if not doc_id:
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"

    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    doc_title = title.strip() or f"Untitled ({doc_id})"
    doc_text = text.strip()

    # 1. Run extractor
    doc_extracted = extract_document(doc_text)
    entities = doc_extracted["entities"]
    relationships = doc_extracted["relationships"]
    sentences = doc_extracted["sentences"]

    # 2. Chunk text
    chunks = chunk_text(sentences, max_chars=800)

    # 3. Create Document node
    db.run_write(
        "CREATE (d:Document {id: $id, title: $title, source: $source, created_at: $created_at, text: $text})",
        {
            "id": doc_id,
            "title": doc_title,
            "source": source,
            "created_at": created_at,
            "text": doc_text,
        },
    )

    # 4. Create Chunk nodes and link (:Document)-[:HAS_CHUNK]->(:Chunk)
    for c in chunks:
        c_id = f"chk_{uuid.uuid4().hex[:8]}"
        c["id"] = c_id
        db.run_write(
            "MATCH (d:Document {id: $doc_id}) "
            "CREATE (c:Chunk {id: $c_id, doc_id: $doc_id, text: $text, position: $position}) "
            "CREATE (d)-[:HAS_CHUNK]->(c)",
            {
                "doc_id": doc_id,
                "c_id": c_id,
                "text": c["text"],
                "position": c["position"],
            },
        )

    # 5. MERGE entities into graph
    for e in entities:
        ent_id = f"ent_{e['label'].lower()}_{uuid.uuid5(uuid.NAMESPACE_DNS, e['name'].lower()).hex[:8]}"
        # Store both :Entity and the specific label :Person, :Project, etc.
        label = e["label"]
        db.run_write(
            f"MERGE (e:Entity:{label} {{name: $name, label: $label}}) "
            f"ON CREATE SET e.id = $id",
            {
                "name": e["name"],
                "label": label,
                "id": ent_id,
            },
        )

    # 6. Link Chunks to Entities (:Chunk)-[:MENTIONS]->(:Entity)
    for c in chunks:
        for e in c["entities"]:
            db.run_write(
                "MATCH (c:Chunk {id: $c_id}), (e:Entity {name: $e_name, label: $e_label}) "
                "MERGE (c)-[:MENTIONS]->(e)",
                {
                    "c_id": c["id"],
                    "e_name": e["name"],
                    "e_label": e["label"],
                },
            )

    # 7. Create Entity-to-Entity relationships
    rels_created = 0
    for r in relationships:
        r_type = r["type"]
        if r_type not in {"WORKS_ON", "USES", "RELATES_TO"}:
            r_type = "RELATES_TO"

        db.run_write(
            f"MATCH (from:Entity {{name: $from_name, label: $from_label}}), "
            f"      (to:Entity {{name: $to_name, label: $to_label}}) "
            f"MERGE (from)-[:{r_type}]->(to)",
            {
                "from_name": r["from"],
                "from_label": r["from_label"],
                "to_name": r["to"],
                "to_label": r["to_label"],
            },
        )
        rels_created += 1

    return {
        "document_id": doc_id,
        "chunks_created": len(chunks),
        "entities_found": len(entities),
        "relationships_created": rels_created,
    }


def delete_document(db: RelateManager, doc_id: str) -> Dict[str, Any]:
    """
    Delete a document, its chunks, and orphan entities that are left with zero connections.
    """
    # Check if doc exists
    doc_res = db.run_read("MATCH (d:Document {id: $id}) RETURN d.id AS id", {"id": doc_id})
    if not doc_res:
        return {"deleted": False, "nodes_removed": 0, "error": "Not found"}

    # Count nodes to be removed
    cnt_chunks = db.run_read(
        "MATCH (d:Document {id: $id})-[:HAS_CHUNK]->(c:Chunk) RETURN count(c) AS cnt",
        {"id": doc_id},
    )
    n_chunks = cnt_chunks[0]["cnt"] if cnt_chunks else 0

    # Delete chunks
    db.run_write(
        "MATCH (d:Document {id: $id})-[:HAS_CHUNK]->(c:Chunk) DETACH DELETE c",
        {"id": doc_id},
    )
    # Delete doc
    db.run_write("MATCH (d:Document {id: $id}) DETACH DELETE d", {"id": doc_id})

    # Delete orphan entities (entities with degree == 0)
    orphan_res = db.run_read("MATCH (e:Entity) WHERE NOT (e)--() RETURN count(e) AS cnt")
    n_orphans = orphan_res[0]["cnt"] if orphan_res else 0
    if n_orphans > 0:
        db.run_write("MATCH (e:Entity) WHERE NOT (e)--() DETACH DELETE e")

    total_removed = 1 + n_chunks + n_orphans
    return {"deleted": True, "nodes_removed": total_removed}
