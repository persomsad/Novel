"""长期记忆系统测试"""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from novel_agent.long_term_memory import LongTermMemory


class TestLongTermMemory:
    """测试长期记忆系统"""

    @pytest.fixture
    def memory(self) -> Generator[LongTermMemory, None, None]:
        """创建临时记忆实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test_memory.db")
            yield LongTermMemory(db_path)

    def test_save_and_get(self, memory: LongTermMemory) -> None:
        """测试保存和获取记忆

        验收标准：
        - 保存记忆后能成功获取
        - 值正确反序列化
        """
        memory.save("user_preference", "writing_style", "第一人称")

        value = memory.get("user_preference", "writing_style")
        assert value == "第一人称"

    def test_get_nonexistent(self, memory: LongTermMemory) -> None:
        """测试获取不存在的记忆

        验收标准：
        - 返回 None
        """
        value = memory.get("user_preference", "nonexistent")
        assert value is None

    def test_save_complex_value(self, memory: LongTermMemory) -> None:
        """测试保存复杂值（字典）

        验收标准：
        - 支持 JSON 可序列化的复杂对象
        """
        character_info = {"name": "李明", "age": 25, "occupation": "程序员"}

        memory.save("project_info", "protagonist", character_info)

        value = memory.get("project_info", "protagonist")
        assert value == character_info
        assert value["name"] == "李明"

    def test_update_existing(self, memory: LongTermMemory) -> None:
        """测试更新已存在的记忆

        验收标准：
        - 更新后的值正确
        """
        memory.save("project_info", "protagonist", "李明")
        memory.save("project_info", "protagonist", "张三")

        value = memory.get("project_info", "protagonist")
        assert value == "张三"

    def test_list_by_category(self, memory: LongTermMemory) -> None:
        """测试列出分类记忆

        验收标准：
        - 返回所有该分类的记忆
        - 按更新时间倒序排列
        """
        memory.save("user_preference", "style", "第一人称")
        memory.save("user_preference", "tone", "轻松幽默")
        memory.save("project_info", "protagonist", "李明")

        memories = memory.list_by_category("user_preference")

        assert len(memories) == 2
        assert any(m["key"] == "style" for m in memories)
        assert any(m["key"] == "tone" for m in memories)

    def test_delete(self, memory: LongTermMemory) -> None:
        """测试删除记忆

        验收标准：
        - 删除成功返回 True
        - 删除后无法获取
        """
        memory.save("user_preference", "style", "第一人称")

        # 删除成功
        assert memory.delete("user_preference", "style") is True

        # 无法获取
        assert memory.get("user_preference", "style") is None

        # 再次删除返回 False
        assert memory.delete("user_preference", "style") is False

    def test_clear_category(self, memory: LongTermMemory) -> None:
        """测试清空分类

        验收标准：
        - 返回删除的数量
        - 该分类的记忆被清空
        """
        memory.save("user_preference", "style", "第一人称")
        memory.save("user_preference", "tone", "轻松幽默")
        memory.save("project_info", "protagonist", "李明")

        count = memory.clear_category("user_preference")

        assert count == 2
        assert len(memory.list_by_category("user_preference")) == 0
        assert len(memory.list_by_category("project_info")) == 1

    def test_save_summary(self, memory: LongTermMemory) -> None:
        """测试保存对话摘要

        验收标准：
        - 保存后能获取
        - 包含所有字段
        """
        memory.save_summary("session123", "讨论了主角设定", 10)

        summary = memory.get_summary("session123")

        assert summary is not None
        assert summary["summary"] == "讨论了主角设定"
        assert summary["message_count"] == 10
        assert "created_at" in summary

    def test_update_summary(self, memory: LongTermMemory) -> None:
        """测试更新对话摘要

        验收标准：
        - 更新后的值正确
        """
        memory.save_summary("session123", "讨论了主角设定", 10)
        memory.save_summary("session123", "讨论了主角设定和世界观", 20)

        summary = memory.get_summary("session123")

        assert summary is not None
        assert summary["summary"] == "讨论了主角设定和世界观"
        assert summary["message_count"] == 20

    def test_search_by_key(self, memory: LongTermMemory) -> None:
        """测试按键搜索

        验收标准：
        - 返回匹配的记忆
        """
        memory.save("project_info", "protagonist_name", "李明")
        memory.save("project_info", "antagonist_name", "张三")
        memory.save("user_preference", "style", "第一人称")

        results = memory.search("name")

        assert len(results) == 2
        assert any(r["key"] == "protagonist_name" for r in results)
        assert any(r["key"] == "antagonist_name" for r in results)

    def test_search_by_value(self, memory: LongTermMemory) -> None:
        """测试按值搜索

        验收标准：
        - 返回匹配的记忆
        """
        memory.save("project_info", "protagonist", "李明")
        memory.save("project_info", "sidekick", "王五")

        results = memory.search("李明")

        assert len(results) == 1
        assert results[0]["key"] == "protagonist"

    def test_search_with_category_filter(self, memory: LongTermMemory) -> None:
        """测试带分类过滤的搜索

        验收标准：
        - 只返回指定分类的记忆
        """
        memory.save("project_info", "protagonist", "李明")
        memory.save("user_preference", "protagonist_style", "第一人称")

        results = memory.search("protagonist", category="project_info")

        assert len(results) == 1
        assert results[0]["category"] == "project_info"

    def test_search_limit(self, memory: LongTermMemory) -> None:
        """测试搜索数量限制

        验收标准：
        - 返回的数量不超过限制
        """
        for i in range(20):
            memory.save("test_category", f"key{i}", f"value{i}")

        results = memory.search("key", limit=5)

        assert len(results) == 5

    def test_get_relevant_memories(self, memory: LongTermMemory) -> None:
        """测试获取相关记忆

        验收标准：
        - 根据上下文返回相关记忆
        """
        memory.save("project_info", "protagonist", "李明")
        memory.save("project_info", "setting", "现代都市")
        memory.save("user_preference", "tone", "轻松幽默")

        results = memory.get_relevant_memories("主角 李明 的职业", limit=2)

        # 应该找到包含"李明"的记忆
        assert len(results) > 0
        assert any("李明" in str(r["value"]) for r in results)

    def test_metadata_support(self, memory: LongTermMemory) -> None:
        """测试元数据支持

        验收标准：
        - 保存和获取元数据
        """
        metadata = {"source": "user_input", "confidence": 0.95}

        memory.save("project_info", "protagonist", "李明", metadata=metadata)

        memories = memory.list_by_category("project_info")

        assert len(memories) == 1
        assert memories[0]["metadata"] == metadata
