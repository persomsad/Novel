"""Error Handling Tests

测试错误处理和日志记录功能
"""

import logging
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from novel_agent.logging_config import get_logger, setup_logging
from novel_agent.tools import read_file, search_content
from novel_agent.tools_file import create_file


class TestLoggingConfig:
    """测试日志配置"""

    def test_setup_logging_default(self) -> None:
        """测试默认日志配置"""
        setup_logging()

        logger = get_logger("test")
        assert logger.level == logging.NOTSET  # 使用父logger的级别

    def test_setup_logging_with_level(self) -> None:
        """测试指定日志级别"""
        setup_logging(level="DEBUG")

        # 验证root logger级别
        root_logger = logging.getLogger("novel_agent")
        assert root_logger.level == logging.DEBUG

    def test_setup_logging_with_file(self) -> None:
        """测试日志文件输出"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            setup_logging(level="INFO", log_file=str(log_file))

            # 写入日志
            logger = get_logger("test")
            logger.info("测试日志消息")

            # 由于日志是异步的，需要flush
            for handler in logging.getLogger().handlers:
                handler.flush()

            # 验证日志文件创建
            assert log_file.exists()


class TestReadFileErrors:
    """测试read_file的错误处理"""

    def test_read_nonexistent_file(self) -> None:
        """测试读取不存在的文件"""
        with pytest.raises(FileNotFoundError, match="文件不存在"):
            read_file("nonexistent-file.txt")

    def test_read_file_permission_error(self) -> None:
        """测试读取无权限的文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建无读权限的文件
            test_file = Path(tmpdir) / "no-permission.txt"
            test_file.write_text("test")
            test_file.chmod(0o000)  # 移除所有权限

            try:
                with pytest.raises(PermissionError):
                    read_file(str(test_file))
            finally:
                # 恢复权限以便清理
                test_file.chmod(0o644)


class TestCreateFileErrors:
    """测试create_file的错误处理"""

    def test_create_file_forbidden_path(self) -> None:
        """测试禁止访问的路径"""
        import os

        # 保存当前目录
        orig_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)

                # 尝试在系统目录创建文件（应该失败）
                with pytest.raises(ValueError, match="禁止操作系统目录"):
                    create_file.invoke({"path": "/usr/test.py", "content": "code"})
        finally:
            os.chdir(orig_cwd)

    def test_create_file_readonly_directory(self) -> None:
        """测试写入只读目录"""
        import os

        orig_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                readonly_dir = Path("readonly")
                readonly_dir.mkdir()
                readonly_dir.chmod(0o444)  # 只读

                try:
                    with pytest.raises(OSError):
                        create_file.invoke({"path": "readonly/test.md", "content": "测试内容"})
                finally:
                    # 恢复权限以便清理
                    readonly_dir.chmod(0o755)
        finally:
            os.chdir(orig_cwd)


class TestSearchContentErrors:
    """测试search_content的错误处理"""

    def test_search_nonexistent_directory(self) -> None:
        """测试搜索不存在的目录"""
        # 使用fallback时，不存在的目录返回空列表
        # 使用ripgrep时，会抛出RuntimeError
        # 测试两种情况都能正确处理
        try:
            results = search_content("关键词", "nonexistent-dir")
            # fallback: 返回空列表
            assert results == []
        except RuntimeError:
            # ripgrep: 抛出错误
            pass

    @patch("novel_agent.tools.subprocess.run")
    def test_search_ripgrep_error(self, mock_run: Any) -> None:
        """测试ripgrep错误处理"""
        # Mock ripgrep返回错误
        mock_run.return_value.returncode = 2
        mock_run.return_value.stderr = "搜索错误"

        with pytest.raises(RuntimeError, match="搜索失败"):
            search_content("关键词", ".")


class TestCLIErrorHandling:
    """测试CLI的错误处理"""

    def test_chat_missing_api_key_error_message(self) -> None:
        """测试缺少API key时的错误提示"""
        from typer.testing import CliRunner

        from novel_agent.cli import app

        runner = CliRunner()

        with patch.dict("os.environ", {}, clear=True):
            result = runner.invoke(app, ["chat"])

            # 应该有友好的错误提示
            assert result.exit_code != 0
            assert "API Key" in result.stdout or "GOOGLE_API_KEY" in result.stdout

    def test_check_nonexistent_file_error_message(self) -> None:
        """测试检查不存在的文件时的错误提示"""
        from typer.testing import CliRunner

        from novel_agent.cli import app

        runner = CliRunner()

        result = runner.invoke(app, ["check", "nonexistent.md", "--api-key", "test"])

        # 应该有友好的错误提示
        assert result.exit_code != 0
        assert "不存在" in result.stdout or "找不到" in result.stdout
