"""
GraphLens - Agent Trace Recorder & Navigable Graph.

Records agent execution steps as (:Trace)-[:HAS_STEP]->(:Step)-[:NEXT]->(:Step) chains
linked via [:TOUCHES] to graph (:Entity) nodes.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any, Dict, List, Optional

from app.graph import RelateManager


def record_trace(
    db: RelateManager,
    name: str,
    steps: List[Dict[str, Any]],
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record an agent trace with chained Step nodes and TOUCHES relationships to entities.
    """
    if not trace_id:
        trace_id = f"tr_{uuid.uuid4().hex[:8]}"

    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    trace_name = name.strip() or f"Trace {trace_id}"

    # 1. Create Trace node
    db.run_write(
        "CREATE (t:Trace {id: $id, name: $name, created_at: $created_at})",
        {"id": trace_id, "name": trace_name, "created_at": created_at},
    )

    prev_step_id: Optional[str] = None
    steps_created = 0

    for idx, s in enumerate(steps):
        step_id = f"step_{trace_id}_{idx}"
        step_name = s.get("name", f"Step {idx + 1}")
        kind = s.get("kind", "tool")  # tool, reasoning, plan, action
        detail = s.get("detail", "")
        ts = s.get("ts", created_at)
        touched_entities = s.get("entities", [])

        # Create Step node and link from Trace
        db.run_write(
            "MATCH (t:Trace {id: $t_id}) "
            "CREATE (s:Step {id: $s_id, trace_id: $t_id, name: $name, kind: $kind, detail: $detail, ts: $ts, position: $position}) "
            "CREATE (t)-[:HAS_STEP]->(s)",
            {
                "t_id": trace_id,
                "s_id": step_id,
                "name": step_name,
                "kind": kind,
                "detail": detail,
                "ts": ts,
                "position": idx,
            },
        )
        steps_created += 1

        # Link to previous step with [:NEXT]
        if prev_step_id:
            db.run_write(
                "MATCH (s1:Step {id: $s1_id}), (s2:Step {id: $s2_id}) "
                "CREATE (s1)-[:NEXT]->(s2)",
                {"s1_id": prev_step_id, "s2_id": step_id},
            )
        prev_step_id = step_id

        # Link to touched entities (:Step)-[:TOUCHES]->(:Entity)
        for ent_name in touched_entities:
            # Check if entity exists or create a Topic/Tool entity
            db.run_write(
                "MERGE (e:Entity {name: $name, label: 'Topic'}) "
                "ON CREATE SET e.id = $ent_id "
                "WITH e "
                "MATCH (s:Step {id: $step_id}) "
                "MERGE (s)-[:TOUCHES]->(e)",
                {
                    "name": ent_name,
                    "ent_id": f"ent_{uuid.uuid5(uuid.NAMESPACE_DNS, ent_name.lower()).hex[:8]}",
                    "step_id": step_id,
                },
            )

    return {
        "trace_id": trace_id,
        "steps_created": steps_created,
    }


def list_traces(db: RelateManager) -> List[Dict[str, Any]]:
    """List all recorded traces with step counts."""
    query = (
        "MATCH (t:Trace) "
        "OPTIONAL MATCH (t)-[:HAS_STEP]->(s:Step) "
        "RETURN t.id AS id, t.name AS name, t.created_at AS created_at, count(s) AS step_count "
        "ORDER BY t.created_at DESC"
    )
    res = db.run_read(query)
    return res


def get_trace_detail(db: RelateManager, trace_id: str) -> Optional[Dict[str, Any]]:
    """Get full trace details with steps ordered and touched entities."""
    t_res = db.run_read(
        "MATCH (t:Trace {id: $id}) RETURN t.id AS id, t.name AS name, t.created_at AS created_at",
        {"id": trace_id},
    )
    if not t_res:
        return None

    trace = t_res[0]

    steps_res = db.run_read(
        "MATCH (t:Trace {id: $id})-[:HAS_STEP]->(s:Step) "
        "OPTIONAL MATCH (s)-[:TOUCHES]->(e:Entity) "
        "RETURN s.id AS id, s.name AS name, s.kind AS kind, s.detail AS detail, "
        "       s.ts AS ts, s.position AS position, collect(e.name) AS entities "
        "ORDER BY s.position ASC",
        {"id": trace_id},
    )

    trace["steps"] = steps_res
    return trace
