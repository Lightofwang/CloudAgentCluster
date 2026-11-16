"""
GraphLens - Rule-based Entity & Relationship Extractor.

Extracts Person, Project, Topic, Tool, and Date entities, along with
WORKS_ON, USES, and RELATES_TO relationships from text without any external API calls.
Deterministic, offline, and transparent.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple


PERSON_GAZETTEER = {
    "Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Heidi",
    "Mallory", "Charlie", "Trent", "Peggy", "Victor", "Walter", "Satoshi",
    "Linus", "Ada", "Alan", "Sam", "Elena", "Marcus", "Sophia", "Liam",
    "Noah", "Maya", "Lucas", "Kira", "Sarah", "Alex", "David", "Leo",
    "Zoe", "Chloe", "Dr. Vance", "Professor Chen"
}

PROJECT_GAZETTEER = {
    "GhostFeed", "LocalScribe", "GraphLens", "AgentMem", "FastTree",
    "DataSync", "CloudAgentCluster", "AutoBench", "DocuGraph", "Kiroween",
    "OpenDev", "NeoFlow", "MemBench", "TraceViewer", "KnowledgeHub",
    "OmniGraph", "ContextEngine", "PromptLog", "QueryCraft"
}

TOPIC_GAZETTEER = {
    "RSS", "AI Agents", "AI Agent", "Agent Memory", "Knowledge Graph",
    "Graph Database", "Vector Search", "Cypher", "Benchmarking",
    "Offline-first", "Local-first", "Context", "Summarization", "RAG",
    "Full-stack", "Privacy", "Decentralization", "Memory Workbench",
    "Connected-Context", "Provenance", "Semantic Search", "Graph RAG",
    "Audit Trail", "Machine Learning", "Embedding", "Observability"
}

TOOL_GAZETTEER = {
    "Python", "FastAPI", "Uvicorn", "Relate", "Docker", "Git", "SQLite",
    "PostgreSQL", "PyTorch", "React", "HTML", "JavaScript", "CSS",
    "Linux", "pytest", "unittest", "cURL", "Neo4j", "NetworkX",
    "Tailwind", "TypeScript", "Node.js", "Pandas", "NumPy", "Arrow", "uv"
}

# Compiled regexes for sentence splitting
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])|\n\s*\n|\n(?=[A-Z0-9\"'*-])")

# Action / cue patterns
WORKS_ON_CUES = re.compile(
    r"\b(?:works\s+on|working\s+on|built|building|builds|created|creates|creating|"
    r"leads|leading|founded|co-founded|started|designed|designing|maintains|joined|"
    r"develops|developing|developed|architected)\b",
    re.IGNORECASE,
)

USES_CUES = re.compile(
    r"\b(?:uses|using|used|built\s+with|powered\s+by|leverages|leveraging|"
    r"runs\s+on|implemented\s+in|written\s+in|relies\s+on|integrates\s+with)\b",
    re.IGNORECASE,
)

DATE_PATTERNS = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),  # 2026-12-11
    re.compile(
        r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
        r"Dec(?:ember)?)\s+\d{1,2}(?:,\s*\d{4})?\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bQ[1-4]\s+\d{4}\b"),  # Q4 2026
]

CAMEL_CASE_PROJECT_RE = re.compile(r"\b[A-Z][a-z0-9]+[A-Z][a-zA-Z0-9]*\b")


def split_into_sentences(text: str) -> List[str]:
    """Split raw text into clean, non-empty sentences."""
    if not text:
        return []
    raw_splits = SENTENCE_SPLIT_RE.split(text.strip())
    sentences = []
    for s in raw_splits:
        s_clean = s.strip()
        if s_clean:
            # Also handle single-line bullet points
            lines = [l.strip().lstrip("-*•0123456789. ") for l in s_clean.split("\n") if l.strip()]
            for line in lines:
                if len(line) > 1:
                    sentences.append(line)
    return sentences


def extract_entities(sentence: str) -> List[Dict[str, str]]:
    """Extract entities (Person, Project, Topic, Tool, Date) from a sentence."""
    found: Dict[Tuple[str, str], Dict[str, str]] = {}

    def _add(name: str, label: str):
        cleaned = name.strip().strip(",.;:\"'()")
        if len(cleaned) < 2:
            return
        key = (label, cleaned.lower())
        if key not in found:
            found[key] = {"name": cleaned, "label": label}

    # 1. Dates
    for d_pat in DATE_PATTERNS:
        for m in d_pat.finditer(sentence):
            _add(m.group(0), "Date")

    # 2. Persons
    for p in PERSON_GAZETTEER:
        if re.search(r"\b" + re.escape(p) + r"\b", sentence, re.IGNORECASE):
            _add(p, "Person")

    # Person regex cue: e.g. "Sarah works on..."
    person_cue_match = re.finditer(
        r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+(?:works\s+on|built|leads|joined|created)",
        sentence,
    )
    for m in person_cue_match:
        cand = m.group(1).strip()
        if cand not in {"The", "This", "Our", "Their", "We", "He", "She", "It"}:
            _add(cand, "Person")

    # 3. Projects
    for prj in PROJECT_GAZETTEER:
        if re.search(r"\b" + re.escape(prj) + r"\b", sentence, re.IGNORECASE):
            _add(prj, "Project")

    # CamelCase candidates
    for m in CAMEL_CASE_PROJECT_RE.finditer(sentence):
        cand = m.group(0)
        # Avoid common words that are capitalized at sentence starts
        if cand not in {"FastAPI", "SQLite", "PostgreSQL", "JavaScript", "TypeScript", "PyTorch", "Neo4j"}:
            if cand not in found:
                _add(cand, "Project")

    # Project explicit cue: e.g. "project GhostFeed", "tool called FastTree"
    # Note: don't use re.IGNORECASE for [A-Z] name match
    proj_cue_matches = re.finditer(
        r"\b(?:project|app|workbench|system|prototype)\s+([A-Z][A-Za-z0-9_-]+)\b",
        sentence,
    )
    stop_projects = {
        "The", "A", "An", "This", "That", "It", "Focuses", "Aims", "Uses",
        "Provides", "Runs", "Handles", "Stores", "Builds", "Enables"
    }
    for m in proj_cue_matches:
        cand = m.group(1).strip()
        if cand not in stop_projects and len(cand) > 2:
            _add(cand, "Project")

    # 4. Tools
    for tool in TOOL_GAZETTEER:
        if re.search(r"\b" + re.escape(tool) + r"\b", sentence, re.IGNORECASE):
            _add(tool, "Tool")

    # 5. Topics
    for topic in TOPIC_GAZETTEER:
        if re.search(r"\b" + re.escape(topic) + r"\b", sentence, re.IGNORECASE):
            _add(topic, "Topic")

    return list(found.values())


def extract_relationships(
    sentence: str, entities: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """Extract relationships between entities co-occurring in the sentence."""
    if len(entities) < 2:
        return []

    rels: List[Dict[str, str]] = []
    seen: Set[Tuple[str, str, str]] = set()

    def _add_rel(source: Dict[str, str], target: Dict[str, str], rel_type: str):
        s_name, s_lbl = source["name"], source["label"]
        t_name, t_lbl = target["name"], target["label"]
        if s_name.lower() == t_name.lower():
            return
        key = (s_name, t_name, rel_type)
        if key not in seen:
            seen.add(key)
            rels.append({
                "from": s_name,
                "from_label": s_lbl,
                "to": t_name,
                "to_label": t_lbl,
                "type": rel_type,
            })

    has_works_on = bool(WORKS_ON_CUES.search(sentence))
    has_uses = bool(USES_CUES.search(sentence))

    persons = [e for e in entities if e["label"] == "Person"]
    projects = [e for e in entities if e["label"] == "Project"]
    tools = [e for e in entities if e["label"] == "Tool"]
    topics = [e for e in entities if e["label"] == "Topic"]
    dates = [e for e in entities if e["label"] == "Date"]

    # 1. Person -> Project (WORKS_ON)
    for p in persons:
        for prj in projects:
            if has_works_on or len(entities) == 2:
                _add_rel(p, prj, "WORKS_ON")
            else:
                _add_rel(p, prj, "RELATES_TO")

    # 2. Entity -> Tool (USES)
    for t in tools:
        for source in (persons + projects):
            if has_uses or len(entities) == 2:
                _add_rel(source, t, "USES")
            else:
                _add_rel(source, t, "RELATES_TO")

    # 3. Project -> Topic (RELATES_TO)
    for prj in projects:
        for top in topics:
            _add_rel(prj, top, "RELATES_TO")

    # 4. Project / Person -> Date (RELATES_TO)
    for d in dates:
        for source in (projects + persons):
            _add_rel(source, d, "RELATES_TO")

    # 5. Connect remaining pairs if not already linked
    for i in range(len(entities)):
        for j in range(i + 1, len(entities)):
            e1, e2 = entities[i], entities[j]
            # If neither direction linked
            if not any(
                (r["from"] == e1["name"] and r["to"] == e2["name"])
                or (r["from"] == e2["name"] and r["to"] == e1["name"])
                for r in rels
            ):
                _add_rel(e1, e2, "RELATES_TO")

    return rels


def extract_document(text: str) -> Dict[str, Any]:
    """
    Extract all entities, sentence chunks, and relationships from a full document.
    """
    sentences = split_into_sentences(text)
    all_entities_map: Dict[Tuple[str, str], Dict[str, str]] = {}
    all_relationships: List[Dict[str, str]] = []
    sentence_records: List[Dict[str, Any]] = []

    for idx, sentence in enumerate(sentences):
        sent_entities = extract_entities(sentence)
        sent_rels = extract_relationships(sentence, sent_entities)

        for e in sent_entities:
            key = (e["label"], e["name"].lower())
            if key not in all_entities_map:
                all_entities_map[key] = e

        all_relationships.extend(sent_rels)

        sentence_records.append({
            "position": idx,
            "text": sentence,
            "entities": sent_entities,
            "relationships": sent_rels,
        })

    # Deduplicate relationships across sentences
    dedup_rels: List[Dict[str, str]] = []
    rel_seen: Set[Tuple[str, str, str]] = set()
    for r in all_relationships:
        key = (r["from"], r["to"], r["type"])
        if key not in rel_seen:
            rel_seen.add(key)
            dedup_rels.append(r)

    return {
        "entities": list(all_entities_map.values()),
        "relationships": dedup_rels,
        "sentences": sentence_records,
    }
