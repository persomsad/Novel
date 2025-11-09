"""长期记忆系统

支持跨会话的知识保存和检索：
- 用户偏好记忆（写作风格、常用设定等）
- 项目信息记忆（角色、世界观、情节要点）
- 自动摘要（总结长对话的关键信息）
"""

import json
import sqlite3
from pathlib import Path
from typing import Any


class LongTermMemory:
    """长期记忆管理器"""

    def __init__(self, db_path: str = ".novel-agent/memory.db"):
        """初始化长期记忆

        Args:
            db_path: SQLite 数据库路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, key)
                );

                CREATE INDEX IF NOT EXISTS idx_category ON memories(category);
                CREATE INDEX IF NOT EXISTS idx_key ON memories(key);

                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    message_count INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(session_id)
                );

                CREATE INDEX IF NOT EXISTS idx_session ON conversation_summaries(session_id);
                """
            )

    def save(
        self, category: str, key: str, value: Any, metadata: dict[str, Any] | None = None
    ) -> None:
        """保存记忆

        Args:
            category: 分类（user_preference/project_info/character_info等）
            key: 键（如 "protagonist_name", "writing_style"）
            value: 值（任意 JSON 可序列化的对象）
            metadata: 元数据（可选）
        """
        value_json = json.dumps(value, ensure_ascii=False)
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO memories (category, key, value, metadata, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(category, key)
                DO UPDATE SET value = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP
                """,
                (category, key, value_json, metadata_json, value_json, metadata_json),
            )

    def get(self, category: str, key: str) -> Any | None:
        """获取记忆

        Args:
            category: 分类
            key: 键

        Returns:
            值（如果存在），否则返回 None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value FROM memories WHERE category = ? AND key = ?",
                (category, key),
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None

    def list_by_category(self, category: str) -> list[dict[str, Any]]:
        """列出指定分类的所有记忆

        Args:
            category: 分类

        Returns:
            记忆列表
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT key, value, metadata, created_at, updated_at
                FROM memories
                WHERE category = ?
                ORDER BY updated_at DESC
                """,
                (category,),
            )
            results = []
            for row in cursor.fetchall():
                results.append(
                    {
                        "key": row[0],
                        "value": json.loads(row[1]),
                        "metadata": json.loads(row[2]) if row[2] else None,
                        "created_at": row[3],
                        "updated_at": row[4],
                    }
                )
            return results

    def delete(self, category: str, key: str) -> bool:
        """删除记忆

        Args:
            category: 分类
            key: 键

        Returns:
            是否删除成功
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM memories WHERE category = ? AND key = ?",
                (category, key),
            )
            return cursor.rowcount > 0

    def clear_category(self, category: str) -> int:
        """清空指定分类的所有记忆

        Args:
            category: 分类

        Returns:
            删除的记忆数量
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM memories WHERE category = ?", (category,))
            return cursor.rowcount

    def save_summary(self, session_id: str, summary: str, message_count: int) -> None:
        """保存对话摘要

        Args:
            session_id: 会话ID
            summary: 对话摘要
            message_count: 消息数量
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO conversation_summaries (session_id, summary, message_count)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id)
                DO UPDATE SET summary = ?, message_count = ?, created_at = CURRENT_TIMESTAMP
                """,
                (session_id, summary, message_count, summary, message_count),
            )

    def get_summary(self, session_id: str) -> dict[str, Any] | None:
        """获取对话摘要

        Args:
            session_id: 会话ID

        Returns:
            摘要信息（如果存在）
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT summary, message_count, created_at
                   FROM conversation_summaries
                   WHERE session_id = ?""",
                (session_id,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "summary": row[0],
                    "message_count": row[1],
                    "created_at": row[2],
                }
            return None

    def search(
        self, query: str, category: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """搜索记忆

        Args:
            query: 搜索关键词
            category: 分类过滤（可选）
            limit: 返回数量限制

        Returns:
            匹配的记忆列表
        """
        with sqlite3.connect(self.db_path) as conn:
            if category:
                cursor = conn.execute(
                    """
                    SELECT category, key, value, metadata, created_at, updated_at
                    FROM memories
                    WHERE category = ? AND (key LIKE ? OR value LIKE ?)
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (category, f"%{query}%", f"%{query}%", limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT category, key, value, metadata, created_at, updated_at
                    FROM memories
                    WHERE key LIKE ? OR value LIKE ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (f"%{query}%", f"%{query}%", limit),
                )

            results = []
            for row in cursor.fetchall():
                results.append(
                    {
                        "category": row[0],
                        "key": row[1],
                        "value": json.loads(row[2]),
                        "metadata": json.loads(row[3]) if row[3] else None,
                        "created_at": row[4],
                        "updated_at": row[5],
                    }
                )
            return results

    def get_relevant_memories(self, context: str, limit: int = 5) -> list[dict[str, Any]]:
        """获取与上下文相关的记忆

        Args:
            context: 上下文文本
            limit: 返回数量限制

        Returns:
            相关记忆列表
        """
        # 简单实现：提取关键词并搜索
        keywords = context.split()[:10]  # 取前10个词
        all_results = []

        for keyword in keywords:
            results = self.search(keyword, limit=limit)
            all_results.extend(results)

        # 去重并按更新时间排序
        seen = set()
        unique_results = []
        for result in all_results:
            key = (result["category"], result["key"])
            if key not in seen:
                seen.add(key)
                unique_results.append(result)

        return unique_results[:limit]


# 全局实例
_global_memory: LongTermMemory | None = None


def get_memory() -> LongTermMemory:
    """获取全局记忆实例"""
    global _global_memory
    if _global_memory is None:
        _global_memory = LongTermMemory()
    return _global_memory


__all__ = ["LongTermMemory", "get_memory"]
