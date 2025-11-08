"""Tests for novel_agent.tools"""

from pathlib import Path

import pytest

from novel_agent.tools import (
    read_file,
    search_content,
    verify_strict_references,
    verify_strict_timeline,
    write_chapter,
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


class TestWriteChapter:
    """测试 write_chapter 函数"""

    def test_write_chapter_basic(self, tmp_path: Path) -> None:
        """测试创建基本章节"""
        content = "# Chapter 1\n\nOnce upon a time..."
        result = write_chapter(1, content, str(tmp_path))

        assert result == str(tmp_path / "ch001.md")
        assert Path(result).exists()
        assert Path(result).read_text(encoding="utf-8") == content

    def test_write_chapter_formatting(self, tmp_path: Path) -> None:
        """测试章节编号格式化"""
        write_chapter(1, "content", str(tmp_path))
        write_chapter(99, "content", str(tmp_path))
        write_chapter(999, "content", str(tmp_path))

        assert (tmp_path / "ch001.md").exists()
        assert (tmp_path / "ch099.md").exists()
        assert (tmp_path / "ch999.md").exists()

    def test_write_chapter_invalid_number(self, tmp_path: Path) -> None:
        """测试无效章节编号"""
        with pytest.raises(ValueError, match="章节编号必须在 1-999 之间"):
            write_chapter(0, "content", str(tmp_path))

        with pytest.raises(ValueError, match="章节编号必须在 1-999 之间"):
            write_chapter(1000, "content", str(tmp_path))

    def test_write_chapter_creates_directory(self, tmp_path: Path) -> None:
        """测试自动创建目录"""
        chapters_dir = tmp_path / "new_chapters"
        result = write_chapter(1, "content", str(chapters_dir))

        assert chapters_dir.exists()
        assert Path(result).exists()


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

    def test_verify_timeline_empty(self) -> None:
        """测试时间线验证（空结果）"""
        result = verify_strict_timeline()

        assert "errors" in result
        assert "warnings" in result
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)


class TestVerifyStrictReferences:
    """测试 verify_strict_references 函数"""

    def test_verify_references_empty(self) -> None:
        """测试引用验证（空结果）"""
        result = verify_strict_references()

        assert "errors" in result
        assert "warnings" in result
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)
