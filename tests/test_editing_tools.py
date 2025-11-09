"""Tests for novel_agent.tools - Editing Tools

测试精准编辑工具：
- edit_chapter_lines
- replace_in_file
- multi_edit
"""

from pathlib import Path

import pytest

from novel_agent.tools import edit_chapter_lines, multi_edit, replace_in_file


class TestEditChapterLines:
    """测试 edit_chapter_lines 函数"""

    def test_edit_single_line(self, tmp_path: Path) -> None:
        """测试修改单行"""
        # 创建测试章节
        chapter_path = tmp_path / "ch001.md"
        original_content = "# 第一章\n\n第一行\n第二行\n第三行\n"
        chapter_path.write_text(original_content, encoding="utf-8")

        # 修改第3行（第一行）
        result = edit_chapter_lines(1, 3, 3, "修改后的第一行\n", str(tmp_path))

        assert "✅ 成功修改" in result
        assert "第 3-3 行" in result

        # 验证内容
        new_content = chapter_path.read_text(encoding="utf-8")
        lines = new_content.splitlines()
        assert lines[2] == "修改后的第一行"
        assert lines[3] == "第二行"
        assert lines[4] == "第三行"

    def test_edit_multiple_lines(self, tmp_path: Path) -> None:
        """测试修改多行"""
        chapter_path = tmp_path / "ch001.md"
        original_content = "# 标题\n\n第1段\n第2段\n第3段\n第4段\n"
        chapter_path.write_text(original_content, encoding="utf-8")

        # 修改第3-4行（第1-2段）
        new_content = "新的第1段\n新的第2段\n"
        result = edit_chapter_lines(1, 3, 4, new_content, str(tmp_path))

        assert "✅ 成功修改" in result

        # 验证内容
        updated = chapter_path.read_text(encoding="utf-8")
        assert "新的第1段" in updated
        assert "新的第2段" in updated
        assert "第3段" in updated  # 保留后续内容

    def test_edit_invalid_chapter_number(self, tmp_path: Path) -> None:
        """测试无效章节编号"""
        with pytest.raises(ValueError, match="章节编号必须 >= 1"):
            edit_chapter_lines(0, 1, 1, "content", str(tmp_path))

        with pytest.raises(ValueError, match="章节编号必须 >= 1"):
            edit_chapter_lines(-1, 1, 1, "content", str(tmp_path))

    def test_edit_invalid_line_numbers(self, tmp_path: Path) -> None:
        """测试无效行号"""
        chapter_path = tmp_path / "ch001.md"
        chapter_path.write_text("line1\nline2\n", encoding="utf-8")

        # start_line < 1
        with pytest.raises(ValueError, match="行号无效"):
            edit_chapter_lines(1, 0, 1, "content", str(tmp_path))

        # end_line < start_line
        with pytest.raises(ValueError, match="行号无效"):
            edit_chapter_lines(1, 5, 2, "content", str(tmp_path))

    def test_edit_line_out_of_range(self, tmp_path: Path) -> None:
        """测试行号超出范围"""
        chapter_path = tmp_path / "ch001.md"
        chapter_path.write_text("line1\nline2\nline3\n", encoding="utf-8")

        # end_line 超出文件总行数
        with pytest.raises(ValueError, match="超出文件总行数"):
            edit_chapter_lines(1, 1, 10, "content", str(tmp_path))

    def test_edit_nonexistent_chapter(self, tmp_path: Path) -> None:
        """测试修改不存在的章节"""
        with pytest.raises(FileNotFoundError, match="章节不存在"):
            edit_chapter_lines(999, 1, 1, "content", str(tmp_path))

    def test_edit_preserves_encoding(self, tmp_path: Path) -> None:
        """测试保持 UTF-8 编码（中文）"""
        chapter_path = tmp_path / "ch001.md"
        original = "# 标题\n\n第一段：你好世界\n第二段：再见\n"
        chapter_path.write_text(original, encoding="utf-8")

        edit_chapter_lines(1, 3, 3, "第一段：修改后的中文内容\n", str(tmp_path))

        updated = chapter_path.read_text(encoding="utf-8")
        assert "修改后的中文内容" in updated
        assert "再见" in updated


class TestReplaceInFile:
    """测试 replace_in_file 函数"""

    def test_replace_all_occurrences(self, tmp_path: Path) -> None:
        """测试替换所有出现"""
        test_file = tmp_path / "test.md"
        original = "张三说：你好。张三笑了。张三离开了。"
        test_file.write_text(original, encoding="utf-8")

        result = replace_in_file(str(test_file), "张三", "李四")

        assert "✅ 成功替换 3 处文本" in result
        assert "共出现 3 次" in result

        # 验证内容
        updated = test_file.read_text(encoding="utf-8")
        assert "张三" not in updated
        assert updated.count("李四") == 3

    def test_replace_first_occurrence(self, tmp_path: Path) -> None:
        """测试只替换第一次出现"""
        test_file = tmp_path / "test.md"
        original = "主角出场。主角战斗。主角胜利。"
        test_file.write_text(original, encoding="utf-8")

        result = replace_in_file(str(test_file), "主角", "林逸", occurrence=1)

        assert "✅ 成功替换 1 处文本" in result

        # 验证内容
        updated = test_file.read_text(encoding="utf-8")
        lines = updated.split("。")
        assert "林逸" in lines[0]  # 第一次被替换
        assert "主角" in lines[1]  # 第二次未替换
        assert "主角" in lines[2]  # 第三次未替换

    def test_replace_nth_occurrence(self, tmp_path: Path) -> None:
        """测试替换第 N 次出现"""
        test_file = tmp_path / "test.md"
        original = "AAA BBB AAA CCC AAA"
        test_file.write_text(original, encoding="utf-8")

        # 只替换第2次出现的 "AAA"
        replace_in_file(str(test_file), "AAA", "XXX", occurrence=2)

        updated = test_file.read_text(encoding="utf-8")
        parts = updated.split()
        assert parts[0] == "AAA"  # 第1次未替换
        assert parts[2] == "XXX"  # 第2次被替换
        assert parts[4] == "AAA"  # 第3次未替换

    def test_replace_nonexistent_text(self, tmp_path: Path) -> None:
        """测试替换不存在的文本"""
        test_file = tmp_path / "test.md"
        test_file.write_text("Some content", encoding="utf-8")

        with pytest.raises(ValueError, match="未找到要替换的文本"):
            replace_in_file(str(test_file), "nonexistent", "replacement")

    def test_replace_invalid_occurrence(self, tmp_path: Path) -> None:
        """测试无效的 occurrence 参数"""
        test_file = tmp_path / "test.md"
        test_file.write_text("AAA BBB AAA", encoding="utf-8")

        # occurrence 超出范围
        with pytest.raises(ValueError, match="occurrence 参数无效"):
            replace_in_file(str(test_file), "AAA", "XXX", occurrence=5)

        # occurrence < 1
        with pytest.raises(ValueError, match="occurrence 参数无效"):
            replace_in_file(str(test_file), "AAA", "XXX", occurrence=0)

    def test_replace_file_not_found(self) -> None:
        """测试文件不存在"""
        with pytest.raises(FileNotFoundError, match="文件不存在"):
            replace_in_file("/nonexistent/file.md", "search", "replace")

    def test_replace_preserves_encoding(self, tmp_path: Path) -> None:
        """测试保持 UTF-8 编码"""
        test_file = tmp_path / "chinese.md"
        original = "这是测试。这是测试。"
        test_file.write_text(original, encoding="utf-8")

        replace_in_file(str(test_file), "测试", "考试")

        updated = test_file.read_text(encoding="utf-8")
        assert "考试" in updated
        assert "测试" not in updated


class TestMultiEdit:
    """测试 multi_edit 函数"""

    def test_multi_edit_replace_multiple_files(self, tmp_path: Path) -> None:
        """测试批量替换多个文件"""
        # 创建测试文件
        file1 = tmp_path / "file1.md"
        file2 = tmp_path / "file2.md"
        file1.write_text("主角是张三", encoding="utf-8")
        file2.write_text("张三说话了", encoding="utf-8")

        operations = [
            {"type": "replace", "file": str(file1), "search": "张三", "replace": "李四"},
            {"type": "replace", "file": str(file2), "search": "张三", "replace": "李四"},
        ]

        result = multi_edit(operations)

        assert "✅ 批量编辑完成" in result
        assert "修改了 2 个文件" in result

        # 验证内容
        assert "李四" in file1.read_text(encoding="utf-8")
        assert "李四" in file2.read_text(encoding="utf-8")
        assert "张三" not in file1.read_text(encoding="utf-8")
        assert "张三" not in file2.read_text(encoding="utf-8")

    def test_multi_edit_mixed_operations(self, tmp_path: Path) -> None:
        """测试混合操作（replace + edit_lines）"""
        # 创建章节文件
        ch1 = tmp_path / "ch001.md"
        ch2 = tmp_path / "ch002.md"
        ch1.write_text("# 第一章\n主角登场\n", encoding="utf-8")
        ch2.write_text("# 第二章\n战斗场景\n", encoding="utf-8")

        operations = [
            {"type": "replace", "file": str(ch1), "search": "主角", "replace": "林逸"},
            {
                "type": "edit_lines",
                "chapter_number": 2,
                "file": str(ch2),
                "start_line": 2,
                "end_line": 2,
                "new_content": "激烈的战斗场景\n",
            },
        ]

        result = multi_edit(operations)

        assert "✅ 批量编辑完成" in result

        # 验证内容
        assert "林逸" in ch1.read_text(encoding="utf-8")
        assert "激烈的战斗场景" in ch2.read_text(encoding="utf-8")

    def test_multi_edit_rollback_on_error(self, tmp_path: Path) -> None:
        """测试失败时回滚所有修改"""
        file1 = tmp_path / "file1.md"
        file1.write_text("original content", encoding="utf-8")

        operations = [
            {"type": "replace", "file": str(file1), "search": "original", "replace": "modified"},
            {
                "type": "replace",
                "file": str(file1),
                "search": "nonexistent",  # 这会失败
                "replace": "fail",
            },
        ]

        # 应该抛出异常并回滚
        with pytest.raises(RuntimeError, match="批量编辑失败，已回滚所有修改"):
            multi_edit(operations)

        # 验证文件内容未被修改（已回滚）
        content = file1.read_text(encoding="utf-8")
        assert content == "original content"

    def test_multi_edit_empty_operations(self) -> None:
        """测试空操作列表"""
        result = multi_edit([])
        assert "⚠️ 没有操作需要执行" in result

    def test_multi_edit_missing_file_parameter(self) -> None:
        """测试缺少 file 参数"""
        operations = [{"type": "replace", "search": "test", "replace": "test2"}]

        with pytest.raises(RuntimeError, match="批量编辑失败"):
            multi_edit(operations)

    def test_multi_edit_invalid_operation_type(self, tmp_path: Path) -> None:
        """测试不支持的操作类型"""
        file1 = tmp_path / "test.md"
        file1.write_text("content", encoding="utf-8")

        operations = [{"type": "invalid_type", "file": str(file1)}]

        with pytest.raises(RuntimeError, match="批量编辑失败"):
            multi_edit(operations)

    def test_multi_edit_auto_detect_chapter_number(self, tmp_path: Path) -> None:
        """测试自动检测章节编号"""
        ch42 = tmp_path / "ch042.md"
        ch42.write_text("line1\nline2\nline3\n", encoding="utf-8")

        operations = [
            {
                "type": "edit_lines",
                "file": str(ch42),
                # 不提供 chapter_number，应该自动从文件名提取
                "start_line": 2,
                "end_line": 2,
                "new_content": "modified line2\n",
            },
        ]

        result = multi_edit(operations)

        assert "✅ 批量编辑完成" in result

        # 验证内容
        content = ch42.read_text(encoding="utf-8")
        assert "modified line2" in content

    def test_multi_edit_deduplicates_files(self, tmp_path: Path) -> None:
        """测试去重文件计数（同一文件多次修改）"""
        file1 = tmp_path / "test.md"
        file1.write_text("AAA BBB CCC", encoding="utf-8")

        operations = [
            {"type": "replace", "file": str(file1), "search": "AAA", "replace": "XXX"},
            {"type": "replace", "file": str(file1), "search": "BBB", "replace": "YYY"},
            {"type": "replace", "file": str(file1), "search": "CCC", "replace": "ZZZ"},
        ]

        result = multi_edit(operations)

        # 应该显示修改了 1 个文件（而不是 3 个）
        assert "修改了 1 个文件" in result
        assert "3 个操作" in result

        # 验证所有修改都生效
        content = file1.read_text(encoding="utf-8")
        assert "XXX YYY ZZZ" == content
