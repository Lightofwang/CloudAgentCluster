"""
GraphLens - Relate embedded graph database connection and execution manager.

Provides thread-safe access to the embedded Relate store by isolating
the DB-API connection (which is thread-affine) inside a dedicated worker thread.
"""

from __future__ import annotations

import concurrent.futures
import os
import queue
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import relate

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STORE_PATH = os.environ.get(
    "GRAPH_STORE_PATH", str(PROJECT_ROOT / "data" / "graphlens.rl")
)


def _serialize_val(val: Any) -> Any:
    """Ensure return values are JSON-serializable."""
    if val is None or isinstance(val, (bool, int, float, str)):
        return val
    if hasattr(val, "to_dict") and callable(val.to_dict):
        return val.to_dict()
    if isinstance(val, (list, tuple)):
        return [_serialize_val(item) for item in val]
    if isinstance(val, dict):
        return {k: _serialize_val(v) for k, v in val.items()}
    if hasattr(val, "text"):
        return str(val.text)
    return str(val)


class RelateManager:
    """Thread-safe manager for Relate embedded database."""

    def __init__(self, store_path: str = DEFAULT_STORE_PATH):
        self.store_path = store_path
        self._q: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._closed = False
        self._worker_thread: Optional[threading.Thread] = None
        self._start_worker()

    def _start_worker(self) -> None:
        # Ensure parent directory exists for file-based stores
        if self.store_path != ":memory:":
            p = Path(self.store_path).resolve()
            p.parent.mkdir(parents=True, exist_ok=True)

        self._worker_thread = threading.Thread(
            target=self._worker_loop, daemon=True, name="RelateWorkerThread"
        )
        self._worker_thread.start()

    def _worker_loop(self) -> None:
        """Worker thread loop owning the thread-affine Relate connection."""
        try:
            conn = relate.connect(self.store_path)
        except Exception as e:
            # Propagate connection failure to first waiting task if any
            while not self._closed:
                try:
                    task = self._q.get(timeout=0.5)
                    if task is None:
                        break
                    _, _, _, fut = task
                    fut.set_exception(e)
                except queue.Empty:
                    continue
            return

        while not self._closed:
            try:
                task = self._q.get(timeout=0.2)
            except queue.Empty:
                continue

            if task is None:
                break

            action, payload, is_write, fut = task
            if action == "execute":
                query, params = payload
                try:
                    t0 = time.perf_counter()
                    cur = conn.execute(query, params or {})
                    if is_write:
                        conn.commit()
                    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

                    # Extract columns
                    cols = list(cur.columns) if hasattr(cur, "columns") and cur.columns else []

                    # Convert rows to dicts
                    rows = []
                    for row in cur:
                        if hasattr(row, "to_dict"):
                            rows.append(_serialize_val(row.to_dict()))
                        elif hasattr(row, "data"):
                            rows.append(_serialize_val(row.data()))
                        else:
                            rows.append(_serialize_val(dict(row)))

                    stats = {}
                    if hasattr(cur, "stats") and cur.stats:
                        try:
                            stats = dict(cur.stats)
                        except Exception:
                            stats = {}

                    fut.set_result({
                        "columns": cols,
                        "rows": rows,
                        "stats": stats,
                        "elapsed_ms": elapsed_ms,
                    })
                except Exception as exc:
                    if is_write:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                    fut.set_exception(exc)
            elif action == "reset":
                try:
                    # Clean all nodes and relationships
                    conn.execute("MATCH (n) DETACH DELETE n")
                    conn.commit()
                    fut.set_result(True)
                except Exception as exc:
                    fut.set_exception(exc)
            elif action == "close":
                try:
                    conn.close()
                    fut.set_result(True)
                except Exception as exc:
                    fut.set_exception(exc)
                break

        try:
            conn.close()
        except Exception:
            pass

    def execute(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        is_write: bool = False,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Execute a Cypher query with optional parameters."""
        if self._closed:
            raise RuntimeError("RelateManager is closed")
        fut: concurrent.futures.Future = concurrent.futures.Future()
        self._q.put(("execute", (query, params or {}), is_write, fut))
        return fut.result(timeout=timeout)

    def run_read(
        self, query: str, params: Optional[Dict[str, Any]] = None, timeout: float = 30.0
    ) -> List[Dict[str, Any]]:
        """Convenience method returning rows for a read query."""
        res = self.execute(query, params=params, is_write=False, timeout=timeout)
        return res["rows"]

    def run_write(
        self, query: str, params: Optional[Dict[str, Any]] = None, timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Convenience method running a mutating query with commit."""
        return self.execute(query, params=params, is_write=True, timeout=timeout)

    def reset_graph(self, timeout: float = 30.0) -> bool:
        """Reset the graph by detaching and deleting all nodes."""
        if self._closed:
            raise RuntimeError("RelateManager is closed")
        fut: concurrent.futures.Future = concurrent.futures.Future()
        self._q.put(("reset", None, True, fut))
        return fut.result(timeout=timeout)

    def is_destructive(self, cypher: str) -> bool:
        """Check if query contains destructive clauses."""
        clean = re.sub(r"//.*", "", cypher)
        clean = re.sub(r"/\*.*?\*/", "", clean, flags=re.DOTALL)
        tokens = re.findall(r"\b[A-Za-z]+\b", clean.upper())
        # Check for DROP, DETACH DELETE, DELETE
        destructive_keywords = {"DROP"}
        for i, tok in enumerate(tokens):
            if tok in destructive_keywords:
                return True
            if tok == "DETACH" and i + 1 < len(tokens) and tokens[i + 1] == "DELETE":
                return True
        return False

    def close(self) -> None:
        """Close connection and stop worker thread."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            fut: concurrent.futures.Future = concurrent.futures.Future()
            self._q.put(("close", None, False, fut))
            try:
                fut.result(timeout=5.0)
            except Exception:
                pass
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=2.0)


_GLOBAL_DB: Optional[RelateManager] = None
_GLOBAL_LOCK = threading.Lock()


def get_db(store_path: Optional[str] = None) -> RelateManager:
    """Return or initialize singleton RelateManager."""
    global _GLOBAL_DB
    with _GLOBAL_LOCK:
        target_path = store_path or DEFAULT_STORE_PATH
        if _GLOBAL_DB is None or _GLOBAL_DB._closed or (_GLOBAL_DB.store_path != target_path and store_path is not None):
            if _GLOBAL_DB is not None and not _GLOBAL_DB._closed:
                _GLOBAL_DB.close()
            _GLOBAL_DB = RelateManager(target_path)
        return _GLOBAL_DB


def reset_db_instance() -> None:
    """Reset the global DB instance (used in tests)."""
    global _GLOBAL_DB
    with _GLOBAL_LOCK:
        if _GLOBAL_DB is not None and not _GLOBAL_DB._closed:
            _GLOBAL_DB.close()
        _GLOBAL_DB = None
