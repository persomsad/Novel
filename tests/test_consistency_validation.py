"""集成测试：验证一致性检查工具"""

from unittest import mock

import pytest

from novel_agent.tools import (
    read_file,
    search_content,
    verify_strict_references,
    verify_strict_timeline,
)


class TestConsistencyTools:
    """测试一致性检查工具"""

    def test_read_character_profile(self) -> None:
        """测试读取角色设定文件"""
        # 读取测试数据
        content = read_file("spec/knowledge/character-profiles.md")

        # 验证内容包含角色信息
        assert "李明" in content
        assert "内向" in content or "缺乏自信" in content
        assert "张强" in content

    def test_search_character_mentions(self) -> None:
        """测试搜索角色名称"""
        # 搜索"李明"在所有章节中的出现
        results = search_content("李明", "chapters")

        # 应该找到至少一个结果
        assert len(results) > 0

        # 验证结果格式
        for result in results:
            assert "file" in result
            assert "line" in result
            assert "content" in result

    def test_verify_timeline_basic(self) -> None:
        """测试时间线验证工具"""
        # 这个工具返回验证报告（字典格式）
        result = verify_strict_timeline()

        # 应该返回dict报告
        assert isinstance(result, dict)
        # 应该包含errors和warnings键
        assert "errors" in result
        assert "warnings" in result

    def test_verify_references_basic(self) -> None:
        """测试引用验证工具"""
        # 这个工具返回验证报告（字典格式）
        result = verify_strict_references()

        # 应该返回dict报告
        assert isinstance(result, dict)
        # 应该包含errors和warnings键
        assert "errors" in result
        assert "warnings" in result

    def test_detect_character_inconsistency_data(self) -> None:
        """测试场景1：测试数据包含角色矛盾"""
        # 读取正常章节
        ch1 = read_file("chapters/ch001.md")
        assert "内向" in ch1 or "紧张" in ch1 or "小声" in ch1

        # 读取矛盾章节
        ch2 = read_file("chapters/ch002-inconsistent.md")
        assert "自信" in ch2 or "大步" in ch2

        # 验证测试数据确实包含矛盾
        # （实际的一致性检查由Agent推理完成，这里只验证数据准备正确）

    def test_detect_timeline_inconsistency_data(self) -> None:
        """测试场景2：测试数据包含时间线问题"""
        ch2 = read_file("chapters/ch002-inconsistent.md")

        # 验证包含多个时间标记
        assert ch2.count("[TIME:") >= 2
        # 验证包含不同日期
        assert "2024-01-16" in ch2
        assert "2024-01-20" in ch2

    def test_detect_reference_inconsistency_data(self) -> None:
        """测试场景3：测试数据包含引用问题"""
        ch3 = read_file("chapters/ch003-references.md")

        # 验证包含引用标记
        assert "[REF:" in ch3
        # 验证包含未定义的引用
        assert "nonexistent-event" in ch3

    def test_search_time_markers(self) -> None:
        """测试搜索时间标记"""
        results = search_content("[TIME:", "chapters")

        # 应该找到时间标记
        assert len(results) > 0

    def test_search_reference_markers(self) -> None:
        """测试搜索引用标记"""
        results = search_content("[REF:", "chapters")

        # 应该找到引用标记
        assert len(results) > 0

    @mock.patch("novel_agent.tools.nervus_cli.cypher_query")
    def test_verify_timeline_nervus_diff(
        self, mock_cypher: mock.Mock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("NERVUSDB_DB_PATH", "demo.nervusdb")
        mock_cypher.return_value = {"rows": []}
        result = verify_strict_timeline()

        # 新格式：errors 是 dict 列表，检查 message 或 type 字段
        has_nervus_error = any(
            "NervusDB" in err.get("message", "") or err.get("type") == "missing_in_nervus"
            for err in result["errors"]
        )
        assert has_nervus_error, result
        monkeypatch.delenv("NERVUSDB_DB_PATH")

    @mock.patch("novel_agent.tools.nervus_cli.cypher_query")
    def test_verify_references_nervus_diff(
        self, mock_cypher: mock.Mock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("NERVUSDB_DB_PATH", "demo.nervusdb")
        mock_cypher.return_value = {"rows": []}
        result = verify_strict_references()

        # 新格式：errors 是 dict 列表，检查 message 或 type 字段
        has_nervus_error = any(
            "NervusDB" in err.get("message", "") or err.get("type") == "missing_in_nervus"
            for err in result["errors"]
        )
        assert has_nervus_error, result
        monkeypatch.delenv("NERVUSDB_DB_PATH")
