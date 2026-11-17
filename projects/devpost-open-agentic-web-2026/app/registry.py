"""Agent registry and trust score calculation with SQLite persistence."""

import contextlib
import json
import os
import re
import sqlite3
import statistics
import time
from typing import List, Optional, Tuple
from app.models import Agent, AgentCreate, TrustBreakdown, Run, RunStep
from app.seed import SEED_AGENTS

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "agentbazaar.db"
)


def calculate_trust_score(
    verifiable: int, calls_ok: int, calls_total: int, p50_latency_ms: int
) -> Tuple[int, TrustBreakdown]:
    """Calculate trust score (0-100) and its 3 breakdown components.

    - verifiable (0-30): Manifest and domain verification
    - success_rate (0-40): calls_ok / calls_total ratio
    - latency (0-30): based on p50 latency (<200ms = 30, >2000ms = 0)
    """
    v_score = max(0, min(30, int(verifiable)))

    if calls_total <= 0:
        s_score = 35
    else:
        ratio = max(0.0, min(1.0, float(calls_ok) / float(calls_total)))
        s_score = int(round(40 * ratio))

    if p50_latency_ms <= 200:
        l_score = 30
    elif p50_latency_ms >= 2000:
        l_score = 0
    else:
        l_score = int(round(30 * (1.0 - (p50_latency_ms - 200) / 1800.0)))
    l_score = max(0, min(30, l_score))

    total = max(0, min(100, v_score + s_score + l_score))
    breakdown = TrustBreakdown(
        verifiable=v_score, success_rate=s_score, latency=l_score
    )
    return total, breakdown


class AgentRegistry:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    @contextlib.contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    capabilities TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    price_range TEXT NOT NULL,
                    hours TEXT NOT NULL,
                    trust_score INTEGER NOT NULL,
                    verifiable_score INTEGER NOT NULL,
                    success_rate_score INTEGER NOT NULL,
                    latency_score INTEGER NOT NULL,
                    calls_total INTEGER NOT NULL,
                    calls_ok INTEGER NOT NULL,
                    p50_latency_ms INTEGER NOT NULL,
                    latencies TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    scenario TEXT NOT NULL,
                    input_data TEXT NOT NULL,
                    status TEXT NOT NULL,
                    steps TEXT NOT NULL,
                    result TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor = conn.execute("SELECT COUNT(*) as count FROM agents")
            row = cursor.fetchone()
            if row and row["count"] == 0:
                self._seed_initial_data(conn)

    def _seed_initial_data(self, conn: sqlite3.Connection):
        for s in SEED_AGENTS:
            score, breakdown = calculate_trust_score(
                verifiable=s.get("verifiable_score", 30),
                calls_ok=s["calls_ok"],
                calls_total=s["calls_total"],
                p50_latency_ms=s["p50_latency_ms"],
            )
            conn.execute(
                """
                INSERT INTO agents (
                    id, name, description, capabilities, endpoint,
                    price_range, hours, trust_score, verifiable_score,
                    success_rate_score, latency_score, calls_total,
                    calls_ok, p50_latency_ms, latencies
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    s["id"],
                    s["name"],
                    s["description"],
                    json.dumps(s["capabilities"], ensure_ascii=False),
                    s["endpoint"],
                    s.get("price_range", "¥50–¥500"),
                    s.get("hours", "09:00–21:00"),
                    score,
                    breakdown.verifiable,
                    breakdown.success_rate,
                    breakdown.latency,
                    s["calls_total"],
                    s["calls_ok"],
                    s["p50_latency_ms"],
                    json.dumps(s.get("latencies", [s["p50_latency_ms"]])),
                ),
            )
        conn.commit()

    def reset_to_seeds(self):
        with self._conn() as conn:
            conn.execute("DELETE FROM agents")
            conn.execute("DELETE FROM runs")
            self._seed_initial_data(conn)

    def _row_to_agent(self, row: sqlite3.Row) -> Agent:
        return Agent(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            capabilities=json.loads(row["capabilities"]),
            endpoint=row["endpoint"],
            price_range=row["price_range"],
            hours=row["hours"],
            trust_score=row["trust_score"],
            trust_breakdown=TrustBreakdown(
                verifiable=row["verifiable_score"],
                success_rate=row["success_rate_score"],
                latency=row["latency_score"],
            ),
            calls_total=row["calls_total"],
            calls_ok=row["calls_ok"],
            p50_latency_ms=row["p50_latency_ms"],
            latencies=json.loads(row["latencies"]),
        )

    def list_agents(
        self, capability: Optional[str] = None, q: Optional[str] = None
    ) -> List[Agent]:
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM agents ORDER BY trust_score DESC, calls_total DESC"
            )
            rows = cursor.fetchall()

        agents = [self._row_to_agent(r) for r in rows]

        if capability:
            cap = capability.strip().lower()
            agents = [a for a in agents if any(c.lower() == cap for c in a.capabilities)]

        if q:
            query = q.strip().lower()
            agents = [
                a
                for a in agents
                if (
                    query in a.name.lower()
                    or query in a.description.lower()
                    or query in a.id.lower()
                    or any(query in c.lower() for c in a.capabilities)
                )
            ]
        return agents

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        with self._conn() as conn:
            cursor = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_agent(row)
        return None

    def create_agent(self, payload: AgentCreate) -> Agent:
        clean_name = re.sub(r"[^\w\s-]", "", payload.name).strip().lower()
        slug = re.sub(r"[-\s]+", "-", clean_name)
        if not slug:
            slug = "agent"
        new_id = f"shop-{slug[:16]}-{int(time.time()) % 10000:04d}"

        endpoint = payload.endpoint or f"/api/agents/{new_id}/invoke"
        price_range = payload.price_range or "¥50–¥500"
        hours = payload.hours or "09:00–21:00"

        verifiable = 30
        calls_total = 0
        calls_ok = 0
        p50 = 150
        score, breakdown = calculate_trust_score(
            verifiable=verifiable,
            calls_ok=calls_ok,
            calls_total=calls_total,
            p50_latency_ms=p50,
        )

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agents (
                    id, name, description, capabilities, endpoint,
                    price_range, hours, trust_score, verifiable_score,
                    success_rate_score, latency_score, calls_total,
                    calls_ok, p50_latency_ms, latencies
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id,
                    payload.name,
                    payload.description,
                    json.dumps(payload.capabilities, ensure_ascii=False),
                    endpoint,
                    price_range,
                    hours,
                    score,
                    breakdown.verifiable,
                    breakdown.success_rate,
                    breakdown.latency,
                    calls_total,
                    calls_ok,
                    p50,
                    json.dumps([p50]),
                ),
            )
            conn.commit()

        return self.get_agent(new_id)

    def record_invocation(self, agent_id: str, ok: bool, latency_ms: int) -> Optional[Agent]:
        with self._conn() as conn:
            cursor = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
            row = cursor.fetchone()
            if not row:
                return None

            calls_total = row["calls_total"] + 1
            calls_ok = row["calls_ok"] + (1 if ok else 0)
            latencies = json.loads(row["latencies"])
            latencies.append(int(latency_ms))
            if len(latencies) > 50:
                latencies = latencies[-50:]

            p50_latency_ms = int(statistics.median(latencies))
            verifiable = row["verifiable_score"]

            score, breakdown = calculate_trust_score(
                verifiable=verifiable,
                calls_ok=calls_ok,
                calls_total=calls_total,
                p50_latency_ms=p50_latency_ms,
            )

            conn.execute(
                """
                UPDATE agents SET
                    calls_total = ?,
                    calls_ok = ?,
                    p50_latency_ms = ?,
                    trust_score = ?,
                    verifiable_score = ?,
                    success_rate_score = ?,
                    latency_score = ?,
                    latencies = ?
                WHERE id = ?
                """,
                (
                    calls_total,
                    calls_ok,
                    p50_latency_ms,
                    score,
                    breakdown.verifiable,
                    breakdown.success_rate,
                    breakdown.latency,
                    json.dumps(latencies),
                    agent_id,
                ),
            )
            conn.commit()

        return self.get_agent(agent_id)

    def save_run(self, run: Run):
        steps_json = json.dumps([s.model_dump() for s in run.steps], ensure_ascii=False)
        result_json = json.dumps(run.result, ensure_ascii=False) if run.result else None
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO runs (
                    run_id, scenario, input_data, status, steps, result, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.scenario,
                    json.dumps(run.input, ensure_ascii=False),
                    run.status,
                    steps_json,
                    result_json,
                    run.created_at,
                ),
            )
            conn.commit()

    def get_run(self, run_id: str) -> Optional[Run]:
        with self._conn() as conn:
            cursor = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if not row:
                return None
            steps_data = json.loads(row["steps"])
            steps = [RunStep(**s) for s in steps_data]
            result_data = json.loads(row["result"]) if row["result"] else None
            return Run(
                run_id=row["run_id"],
                scenario=row["scenario"],
                input=json.loads(row["input_data"]),
                status=row["status"],
                steps=steps,
                result=result_data,
                created_at=row["created_at"],
            )
