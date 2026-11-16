"""
GraphLens - Graph-grounded Question Answering Engine.

Zero-external-API, fully deterministic, inspectable Q&A engine.
Traverses the Relate knowledge graph, computes TF-IDF over text chunks for evidence,
and composes answers with explicit, traceable path citations.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple

from app.extractor import extract_entities
from app.graph import RelateManager

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves", "tell", "show", "find", "list", "give", "know",
}


def _tokenize(text: str) -> List[str]:
    words = re.findall(r"\b[A-Za-z0-9_-]+\b", text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 1]


def compute_tfidf_chunks(
    question: str, chunks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Rank chunks using TF-IDF against question tokens."""
    q_tokens = _tokenize(question)
    if not q_tokens or not chunks:
        return []

    n_docs = len(chunks)
    doc_freqs: Counter = Counter()
    chunk_token_lists = []

    for c in chunks:
        tokens = _tokenize(c.get("text", ""))
        chunk_token_lists.append(tokens)
        for token in set(tokens):
            doc_freqs[token] += 1

    q_tf = Counter(q_tokens)
    scored_chunks = []

    for i, c in enumerate(chunks):
        c_tokens = chunk_token_lists[i]
        c_tf = Counter(c_tokens)
        score = 0.0

        for term, q_cnt in q_tf.items():
            if term in c_tf:
                df = doc_freqs.get(term, 1)
                idf = math.log((1 + n_docs) / (1 + df)) + 1.0
                score += (c_tf[term] / (len(c_tokens) + 1e-6)) * idf * q_cnt

        if score > 0.05:
            scored_chunks.append({
                "id": c.get("id"),
                "text": c.get("text"),
                "score": round(score, 3),
            })

    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    return scored_chunks[:3]


def answer_question(db: RelateManager, question: str) -> Dict[str, Any]:
    """
    Graph-grounded question answering with traceable citations.
    """
    clean_q = question.strip()
    if not clean_q:
        return {
            "answer": "Please ask a question.",
            "citations": [],
            "cypher_used": "",
            "evidence_chunks": [],
        }

    # 1. Identify entities mentioned in the question
    # Check extractor candidates first
    extracted = extract_entities(clean_q)
    matched_entity_names: Set[str] = {e["name"] for e in extracted}

    # Also search against all known entities in DB
    all_ents = db.run_read("MATCH (e:Entity) RETURN e.name AS name, e.label AS label")
    for row in all_ents:
        name = row["name"]
        if re.search(r"\b" + re.escape(name) + r"\b", clean_q, re.IGNORECASE):
            matched_entity_names.add(name)

    # 2. Retrieve graph evidence
    citations: List[Dict[str, Any]] = []
    cypher_used = ""
    graph_facts: List[Dict[str, Any]] = []

    if matched_entity_names:
        cypher_used = (
            "MATCH (a:Entity)-[r]-(b:Entity) "
            "WHERE a.name IN $names "
            "RETURN a.name AS source, a.label AS source_label, type(r) AS rel, "
            "       b.name AS target, b.label AS target_label"
        )
        res = db.run_read(cypher_used, {"names": list(matched_entity_names)})

        edge_weights = {"WORKS_ON": 1.0, "USES": 0.88, "RELATES_TO": 0.75}

        for row in res:
            rel_type = row["rel"]
            score = edge_weights.get(rel_type, 0.7)
            # Directed display string
            path_str = f"[{row['source_label']}:{row['source']}] -{rel_type}-> [{row['target_label']}:{row['target']}]"
            citations.append({
                "path": path_str,
                "score": score,
            })
            graph_facts.append(row)

    # 3. Retrieve text chunk evidence via TF-IDF
    chunks_res = db.run_read("MATCH (c:Chunk) RETURN c.id AS id, c.text AS text")
    evidence_chunks = compute_tfidf_chunks(clean_q, chunks_res)

    # 4. Formulate the answer
    if graph_facts:
        # Group facts by source and relation
        works_on_projects = [
            f["target"] for f in graph_facts
            if f["rel"] == "WORKS_ON" and f["source_label"] == "Person"
        ]
        person_source = [f["source"] for f in graph_facts if f["source_label"] == "Person"]
        main_person = person_source[0] if person_source else list(matched_entity_names)[0]

        uses_tools = [
            f["target"] for f in graph_facts
            if f["rel"] == "USES"
        ]

        relates_to = [
            f"{f['source']} connects to {f['target']}"
            for f in graph_facts
            if f["rel"] == "RELATES_TO"
        ]

        # Check intent cues in question
        q_lower = clean_q.lower()
        sentences = []

        if "work" in q_lower or "working" in q_lower or "project" in q_lower or "who" in q_lower:
            if works_on_projects:
                unique_prjs = sorted(list(set(works_on_projects)))
                if len(unique_prjs) == 1:
                    sentences.append(f"{main_person} works on {unique_prjs[0]}.")
                else:
                    sentences.append(f"{main_person} works on {', '.join(unique_prjs[:-1])} and {unique_prjs[-1]}.")
            elif uses_tools:
                sentences.append(f"{main_person} uses {', '.join(set(uses_tools))}.")

        if not sentences:
            # General summary of retrieved facts
            parts = []
            if works_on_projects:
                parts.append(f"works on {', '.join(set(works_on_projects))}")
            if uses_tools:
                parts.append(f"uses {', '.join(set(uses_tools))}")
            if parts:
                sentences.append(f"{main_person} {' and '.join(parts)}.")
            elif relates_to:
                sentences.append("; ".join(relates_to[:3]) + ".")

        if not sentences and evidence_chunks:
            # Fall back to top chunk summary
            top_sent = evidence_chunks[0]["text"].split(".")[0].strip() + "."
            sentences.append(top_sent)

        citations.sort(key=lambda x: x["score"], reverse=True)
        # Deduplicate citations
        seen_paths = set()
        dedup_citations = []
        for c in citations:
            if c["path"] not in seen_paths:
                seen_paths.add(c["path"])
                dedup_citations.append(c)

        answer_text = " ".join(sentences)
        return {
            "answer": answer_text,
            "citations": dedup_citations[:6],
            "cypher_used": cypher_used,
            "evidence_chunks": evidence_chunks,
        }

    # If no graph facts but we have high-scoring chunk evidence
    if evidence_chunks and evidence_chunks[0]["score"] >= 0.15:
        top_chunk = evidence_chunks[0]
        cypher_used = "MATCH (c:Chunk) RETURN c.id, c.text (TF-IDF ranked)"
        top_sentence = top_chunk["text"].split(".")[0].strip() + "."
        return {
            "answer": f"According to stored notes: {top_sentence}",
            "citations": [{"path": f"[Chunk:{top_chunk['id']}]", "score": top_chunk["score"]}],
            "cypher_used": cypher_used,
            "evidence_chunks": evidence_chunks,
        }

    # Honest fallback
    return {
        "answer": "I couldn't find any connected context about that in your graph.",
        "citations": [],
        "cypher_used": cypher_used or "MATCH (a:Entity) WHERE a.name IN $names RETURN a",
        "evidence_chunks": [],
    }
