"""通用文件操作工具测试"""

from pathlib import Path

import pytest

from novel_agent.tools_file import create_directory, create_file, list_files


class TestFileOperations:
    """文件操作工具测试"""

    def test_create_file_simple(self, tmp_path):
        """测试创建简单文件"""
        # 切换到临时目录
        import os

        os.chdir(tmp_path)

        # 创建文件
        result = create_file.invoke({"path": "test.md", "content": "Hello World"})

        assert result == "test.md"
        assert Path("test.md").exists()
        assert Path("test.md").read_text() == "Hello World"

    def test_create_file_with_directory(self, tmp_path):
        """测试创建文件（自动创建目录）"""
        import os

        os.chdir(tmp_path)

        # 创建文件（目录不存在）
        result = create_file.invoke({"path": "chapters/ch001.md", "content": "# 第一章\n"})

        assert result == "chapters/ch001.md"
        assert Path("chapters/ch001.md").exists()
        assert Path("chapters/ch001.md").read_text() == "# 第一章\n"

    def test_create_file_nested_directory(self, tmp_path):
        """测试创建文件（多级目录）"""
        import os

        os.chdir(tmp_path)

        # 创建多级目录的文件
        result = create_file.invoke({"path": "chapters/卷一/第一部分/ch001.md", "content": "内容"})

        assert result == "chapters/卷一/第一部分/ch001.md"
        assert Path("chapters/卷一/第一部分/ch001.md").exists()

    def test_create_file_overwrite(self, tmp_path):
        """测试覆盖已存在的文件"""
        import os

        os.chdir(tmp_path)

        # 创建文件
        create_file.invoke({"path": "test.md", "content": "旧内容"})

        # 覆盖文件
        result = create_file.invoke({"path": "test.md", "content": "新内容"})

        assert result == "test.md"
        assert Path("test.md").read_text() == "新内容"

    def test_create_file_forbidden_path(self, tmp_path):
        """测试禁止访问的路径"""
        import os

        os.chdir(tmp_path)

        # 创建 src 目录（模拟关键目录）
        Path("src").mkdir()

        # 尝试在 src 目录创建文件（应该失败）
        with pytest.raises(ValueError, match="禁止操作关键目录"):
            create_file.invoke({"path": "src/test.py", "content": "code"})

    def test_create_file_path_traversal(self, tmp_path):
        """测试路径遍历攻击"""
        import os

        os.chdir(tmp_path)

        # 尝试使用 .. 访问外部（应该失败）
        with pytest.raises(ValueError, match="禁止使用相对路径"):
            create_file.invoke({"path": "../outside.md", "content": "hack"})

    def test_create_file_outside_project(self, tmp_path):
        """测试访问项目外部路径"""
        import os

        os.chdir(tmp_path)

        # 尝试访问外部绝对路径（应该失败）
        with pytest.raises(ValueError, match="禁止访问项目外部路径"):
            create_file.invoke({"path": "/tmp/hack.md", "content": "hack"})

    def test_create_directory_simple(self, tmp_path):
        """测试创建简单目录"""
        import os

        os.chdir(tmp_path)

        result = create_directory.invoke({"path": "chapters"})

        assert result == "chapters"
        assert Path("chapters").is_dir()

    def test_create_directory_nested(self, tmp_path):
        """测试创建多级目录"""
        import os

        os.chdir(tmp_path)

        result = create_directory.invoke({"path": "chapters/卷一/第一部分"})

        assert result == "chapters/卷一/第一部分"
        assert Path("chapters/卷一/第一部分").is_dir()

    def test_create_directory_already_exists(self, tmp_path):
        """测试创建已存在的目录"""
        import os

        os.chdir(tmp_path)

        # 创建目录
        create_directory.invoke({"path": "chapters"})

        # 再次创建（应该成功，不报错）
        result = create_directory.invoke({"path": "chapters"})

        assert result == "chapters"
        assert Path("chapters").is_dir()

    def test_create_directory_forbidden(self, tmp_path):
        """测试禁止创建关键目录"""
        import os

        os.chdir(tmp_path)

        # 尝试创建 src 子目录（应该失败）
        Path("src").mkdir()
        with pytest.raises(ValueError, match="禁止操作关键目录"):
            create_directory.invoke({"path": "src/new"})

    def test_list_files_simple(self, tmp_path):
        """测试列出目录内容"""
        import os

        os.chdir(tmp_path)

        # 创建测试文件和目录
        Path("test1.md").write_text("content1")
        Path("test2.md").write_text("content2")
        Path("subdir").mkdir()

        # 列出当前目录
        result = list_files.invoke({"path": "."})

        assert "📁 ." in result
        assert "3 项" in result
        assert "📄 test1.md" in result
        assert "📄 test2.md" in result
        assert "📁 subdir/" in result

    def test_list_files_subdirectory(self, tmp_path):
        """测试列出子目录"""
        import os

        os.chdir(tmp_path)

        # 创建子目录和文件
        Path("chapters").mkdir()
        Path("chapters/ch001.md").write_text("chapter 1")
        Path("chapters/ch002.md").write_text("chapter 2")

        # 列出子目录
        result = list_files.invoke({"path": "chapters"})

        assert "📁 chapters" in result
        assert "2 项" in result
        assert "📄 ch001.md" in result
        assert "📄 ch002.md" in result

    def test_list_files_empty_directory(self, tmp_path):
        """测试列出空目录"""
        import os

        os.chdir(tmp_path)

        # 创建空目录
        Path("empty").mkdir()

        # 列出空目录
        result = list_files.invoke({"path": "empty"})

        assert "空目录" in result

    def test_list_files_not_exist(self, tmp_path):
        """测试列出不存在的目录"""
        import os

        os.chdir(tmp_path)

        # 尝试列出不存在的目录
        with pytest.raises(FileNotFoundError, match="目录不存在"):
            list_files.invoke({"path": "notexist"})

    def test_list_files_is_file(self, tmp_path):
        """测试列出文件（不是目录）"""
        import os

        os.chdir(tmp_path)

        # 创建文件
        Path("test.md").write_text("content")

        # 尝试列出文件（应该失败）
        with pytest.raises(ValueError, match="不是目录"):
            list_files.invoke({"path": "test.md"})

    def test_list_files_sorting(self, tmp_path):
        """测试目录内容排序（目录在前，文件在后）"""
        import os

        os.chdir(tmp_path)

        # 创建混合内容
        Path("b_file.md").write_text("file")
        Path("a_dir").mkdir()
        Path("c_file.md").write_text("file")

        # 列出目录
        result = list_files.invoke({"path": "."})

        # 检查目录在前
        lines = result.split("\n")
        dir_line = next(i for i, line in enumerate(lines) if "a_dir/" in line)
        file_line = next(i for i, line in enumerate(lines) if "b_file.md" in line)
        assert dir_line < file_line  # 目录应该在文件前面
