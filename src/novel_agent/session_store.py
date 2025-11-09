"""Session management helpers for LangGraph SqliteSaver."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from langgraph.checkpoint.sqlite import SqliteSaver

DEFAULT_SESSION_DB = Path(".novel-agent/state.sqlite")


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def open_checkpointer(db_path: Path | None = None) -> Iterator[SqliteSaver]:
    path = Path(db_path or DEFAULT_SESSION_DB)
    _ensure_parent(path)
    with SqliteSaver.from_conn_string(str(path)) as saver:
        yield saver


def list_sessions(db_path: Path | None = None) -> list[str]:
    path = Path(db_path or DEFAULT_SESSION_DB)
    if not path.exists():
        return []
    try:
        conn = sqlite3.connect(path)
    except sqlite3.Error:
        return []
    with conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT,
                checkpoint_ns TEXT,
                checkpoint_id TEXT,
                parent_checkpoint_id TEXT,
                type TEXT,
                checkpoint BLOB,
                metadata BLOB,
                PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
            );
            """
        )
        rows = conn.execute(
            "SELECT thread_id FROM checkpoints GROUP BY thread_id ORDER BY MAX(rowid) DESC"
        ).fetchall()
    return [row[0] for row in rows if row and row[0]]


def delete_session(thread_id: str, db_path: Path | None = None) -> None:
    path = Path(db_path or DEFAULT_SESSION_DB)
    if not path.exists():
        return
    conn = sqlite3.connect(path)
    with conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT,
                checkpoint_ns TEXT,
                checkpoint_id TEXT,
                parent_checkpoint_id TEXT,
                type TEXT,
                checkpoint BLOB,
                metadata BLOB,
                PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
            );
            CREATE TABLE IF NOT EXISTS writes (
                thread_id TEXT,
                checkpoint_ns TEXT,
                checkpoint_id TEXT,
                task_id TEXT,
                idx INTEGER,
                channel TEXT,
                type TEXT,
                value BLOB,
                PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
            );
            """
        )
        conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        conn.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))


__all__ = [
    "DEFAULT_SESSION_DB",
    "open_checkpointer",
    "list_sessions",
    "delete_session",
]
