import sqlite3
from pathlib import Path

from novel_agent import session_store


def test_list_and_delete_sessions(tmp_path: Path) -> None:
    db_path = tmp_path / "state.sqlite"
    conn = sqlite3.connect(db_path)
    with conn:
        conn.executescript(
            """
            CREATE TABLE checkpoints (
                thread_id TEXT,
                checkpoint_ns TEXT,
                checkpoint_id TEXT,
                parent_checkpoint_id TEXT,
                type TEXT,
                checkpoint BLOB,
                metadata BLOB
            );
            CREATE TABLE writes (
                thread_id TEXT,
                checkpoint_ns TEXT,
                checkpoint_id TEXT,
                task_id TEXT,
                idx INTEGER,
                channel TEXT,
                type TEXT,
                value BLOB
            );
            INSERT INTO checkpoints(thread_id, checkpoint_ns, checkpoint_id, type) VALUES
                ('hero', '', '1', 'state'),
                ('villain', '', '1', 'state');
            INSERT INTO writes(
                thread_id, checkpoint_ns, checkpoint_id, task_id,
                idx, channel, type, value
            )
                VALUES ('hero', '', '1', 'task', 0, 'input', 'json', '"hi"');
            """
        )

    sessions = session_store.list_sessions(db_path)
    assert sessions == ["villain", "hero"] or sessions == ["hero", "villain"]

    session_store.delete_session("hero", db_path)
    sessions_after = session_store.list_sessions(db_path)
    assert "hero" not in sessions_after
