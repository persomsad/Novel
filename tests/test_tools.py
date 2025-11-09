"""Tests for novel_agent.tools"""

import json
from pathlib import Path

import pytest

from novel_agent.tools import (
    read_file,
    search_content,
    verify_strict_references,
    verify_strict_timeline,
)


class TestReadFile:
    """测试 read_file 函数"""

    def test_read_existing_file(self, tmp_path: Path) -> None:
        """测试读取存在的文件"""
        test_file = tmp_path / "test.md"
        test_content = "# Test Content\n\nThis is a test."
        test_file.write_text(test_content, encoding="utf-8")

        result = read_file(str(test_file))
        assert result == test_content

    def test_read_nonexistent_file(self) -> None:
        """测试读取不存在的文件"""
        with pytest.raises(FileNotFoundError, match="文件不存在"):
            read_file("/nonexistent/file.md")

    def test_read_file_with_utf8(self, tmp_path: Path) -> None:
        """测试读取 UTF-8 文件（中文）"""
        test_file = tmp_path / "chinese.md"
        test_content = "# 测试\n\n这是中文内容。"
        test_file.write_text(test_content, encoding="utf-8")

        result = read_file(str(test_file))
        assert result == test_content
        assert "中文" in result


# write_chapter 功能已被通用的 create_file 替代
# 相关测试请参见 tests/test_tools_file.py


class TestSearchContent:
    """测试 search_content 函数"""

    def test_search_basic(self, tmp_path: Path) -> None:
        """测试基本搜索"""
        # 创建测试文件
        file1 = tmp_path / "file1.md"
        file1.write_text("This is a test.\nAnother line.", encoding="utf-8")

        file2 = tmp_path / "file2.md"
        file2.write_text("No match here.", encoding="utf-8")

        results = search_content("test", str(tmp_path))

        assert len(results) >= 1
        assert any("test" in r["content"].lower() for r in results)

    def test_search_chinese(self, tmp_path: Path) -> None:
        """测试搜索中文"""
        test_file = tmp_path / "chinese.md"
        test_file.write_text("主角：林逸\n性格：善良", encoding="utf-8")

        results = search_content("主角", str(tmp_path))

        assert len(results) >= 1
        assert any("主角" in r["content"] for r in results)

    def test_search_no_results(self, tmp_path: Path) -> None:
        """测试无匹配结果"""
        test_file = tmp_path / "test.md"
        test_file.write_text("Some content", encoding="utf-8")

        results = search_content("nonexistent_keyword", str(tmp_path))

        assert results == []


class TestVerifyStrictTimeline:
    """测试 verify_strict_timeline 函数"""

    def test_verify_timeline_empty(self, tmp_path: Path) -> None:
        """测试时间线验证（空结果）"""
        # 创建临时索引文件
        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps({"chapters": [], "references": []}), encoding="utf-8")

        result = verify_strict_timeline(index_path)

        assert "errors" in result
        assert "warnings" in result
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)


class TestVerifyStrictReferences:
    """测试 verify_strict_references 函数"""

    def test_verify_references_empty(self, tmp_path: Path) -> None:
        """测试引用验证（空结果）"""
        # 创建临时索引文件
        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps({"chapters": [], "references": []}), encoding="utf-8")

        result = verify_strict_references(index_path)

        assert "errors" in result
        assert "warnings" in result
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)
