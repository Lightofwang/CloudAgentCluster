"""
GraphLens - Demo Dataset & Seed Generator.

Provides 12 realistic documents and 1 agent execution trace
to immediately populate the Relate graph database with ~40 entities and ~70 relationships.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.graph import RelateManager
from app.ingest import ingest_document
from app.traces import record_trace

DEMO_DOCUMENTS: List[Dict[str, str]] = [
    {
        "title": "Kiroween Hackathon Notes",
        "source": "notes/kiroween.md",
        "text": (
            "Alice is working on GhostFeed using Python and FastAPI. "
            "GhostFeed integrates RSS feeds with a Knowledge Graph to build an intelligent news reader. "
            "The project focuses on Connected-Context and Offline-first agent memory."
        ),
    },
    {
        "title": "LocalScribe Agent Memory Workbench",
        "source": "notes/localscribe.md",
        "text": (
            "Bob leads LocalScribe built with Python and SQLite. "
            "LocalScribe explores Agent Memory and Local-first architecture for AI agents. "
            "The system ensures user Privacy and eliminates external cloud dependencies."
        ),
    },
    {
        "title": "Graph Databases for AI Agents Survey",
        "source": "research/graph_agents.md",
        "text": (
            "Carol researches Graph Database architectures using Relate and Neo4j. "
            "She is evaluating Cypher queries and Connected-Context graph retrieval for AI Agents. "
            "Relate offers an embedded, zero-server Cypher engine for Python applications."
        ),
    },
    {
        "title": "AgentMem Decentralized Runtime",
        "source": "projects/agentmem.md",
        "text": (
            "Dave works on AgentMem using Docker and Linux. "
            "Alice joined AgentMem to assist with Context management and Decentralization. "
            "The project leverages SQLite for caching and Relate for structured entity storage."
        ),
    },
    {
        "title": "FastTree Vector & Graph Hybrid",
        "source": "experiments/fasttree.md",
        "text": (
            "Eve created FastTree leveraging Vector Search and Relate. "
            "FastTree evaluates Graph RAG for multi-document Summarization. "
            "The tool is implemented in Python and tested with pytest."
        ),
    },
    {
        "title": "TraceViewer Observability Tool",
        "source": "tools/traceviewer.md",
        "text": (
            "Frank maintains TraceViewer written in React and TypeScript. "
            "TraceViewer monitors AI Agents execution and produces an interactive Audit Trail. "
            "The system provides complete Provenance and inspectable decision graphs."
        ),
    },
    {
        "title": "NeoFlow Machine Learning Pipeline",
        "source": "pipelines/neoflow.md",
        "text": (
            "Grace architected NeoFlow using Python and Git. "
            "NeoFlow orchestrates Machine Learning workflows for autonomous AI Agents. "
            "It integrates closely with Relate to store dependency graphs."
        ),
    },
    {
        "title": "DataSync Protocol Specification",
        "source": "specs/datasync.md",
        "text": (
            "Heidi leads DataSync powered by SQLite and Python. "
            "DataSync provides Privacy and Offline-first state synchronization for distributed nodes. "
            "The protocol targets Connected-Context applications."
        ),
    },
    {
        "title": "Graph RAG Fusion Architecture",
        "source": "architecture/graph_rag.md",
        "text": (
            "Alice and Bob collaborate on Graph RAG using FastAPI and Relate. "
            "They combine Semantic Search with Knowledge Graph traversals. "
            "The architecture drastically improves reasoning fidelity for AI Agents."
        ),
    },
    {
        "title": "MemBench Agent Memory Benchmarking",
        "source": "benchmarks/membench.md",
        "text": (
            "Charlie created MemBench using PyTorch and Python. "
            "MemBench evaluates Agent Memory benchmarks across diverse reasoning tasks. "
            "The benchmark measures Context retention and retrieval latency."
        ),
    },
    {
        "title": "AutoBench Evaluation Framework",
        "source": "testing/autobench.md",
        "text": (
            "Trent develops AutoBench using pytest and unittest. "
            "AutoBench validates Semantic Search precision and Provenance tracking. "
            "It integrates with Docker for reproducible benchmark environments."
        ),
    },
    {
        "title": "Relate Hackathon Roadmap 2026",
        "source": "roadmap/2026.md",
        "text": (
            "Sam and Maya organized the Relate Hackathon with submission deadline 2026-12-11. "
            "The core theme highlights Connected-Context and Memory Workbench innovations. "
            "Developers build full-stack tools on top of the embedded Relate database."
        ),
    },
]

DEMO_TRACE: Dict[str, Any] = {
    "name": "nightly-digest-agent",
    "steps": [
        {
            "name": "Fetch Feed Items",
            "kind": "tool",
            "detail": "Retrieved 15 new RSS articles from tech aggregators",
            "entities": ["RSS", "GhostFeed"],
        },
        {
            "name": "Extract Graph Entities",
            "kind": "plan",
            "detail": "Extracted Person, Project, and Tool nodes into Relate store",
            "entities": ["Knowledge Graph", "Relate"],
        },
        {
            "name": "Synthesize Connected Context",
            "kind": "action",
            "detail": "Traversed 2-hop neighbourhood to generate cited summary",
            "entities": ["Agent Memory", "Context"],
        },
        {
            "name": "Dispatch Daily Digest",
            "kind": "tool",
            "detail": "Published digest card and updated execution graph",
            "entities": ["FastAPI", "TraceViewer"],
        },
    ],
}


def seed_demo_data(db: RelateManager) -> Dict[str, Any]:
    """Seed the database with 12 documents and 1 demo trace."""
    docs_created = 0
    total_chunks = 0
    total_entities_found = 0
    total_rels_created = 0

    for idx, doc in enumerate(DEMO_DOCUMENTS):
        doc_id = f"doc_{idx + 1:02d}"
        res = ingest_document(
            db=db,
            title=doc["title"],
            text=doc["text"],
            source=doc["source"],
            doc_id=doc_id,
        )
        docs_created += 1
        total_chunks += res["chunks_created"]
        total_entities_found += res["entities_found"]
        total_rels_created += res["relationships_created"]

    # Seed demo trace
    trace_res = record_trace(
        db=db,
        name=DEMO_TRACE["name"],
        steps=DEMO_TRACE["steps"],
        trace_id="tr_demo_01",
    )

    # Fetch total counts from the graph
    doc_count = db.run_read("MATCH (d:Document) RETURN count(d) AS cnt")[0]["cnt"]
    chunk_count = db.run_read("MATCH (c:Chunk) RETURN count(c) AS cnt")[0]["cnt"]
    entity_count = db.run_read("MATCH (e:Entity) RETURN count(e) AS cnt")[0]["cnt"]
    rel_count = db.run_read("MATCH ()-[r]->() RETURN count(r) AS cnt")[0]["cnt"]
    step_count = db.run_read("MATCH (s:Step) RETURN count(s) AS cnt")[0]["cnt"]

    return {
        "documents": doc_count,
        "chunks": chunk_count,
        "entities": entity_count,
        "relationships": rel_count,
        "steps": step_count,
    }


def reset_and_seed(db: RelateManager) -> Dict[str, Any]:
    """Wipe the database and reseed with clean demo data."""
    db.reset_graph()
    return seed_demo_data(db)
