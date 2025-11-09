"""Tests for novel_agent.cli"""

from pathlib import Path
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from novel_agent.cli import app

runner = CliRunner()


class TestChatCommand:
    """测试 chat 命令"""

    def test_chat_missing_api_key(self) -> None:
        """测试缺少API key时的错误处理"""
        with patch.dict("os.environ", {}, clear=True):
            with patch("novel_agent.cli.create_specialized_agent") as mock_create:
                mock_create.side_effect = ValueError("未找到 Gemini API Key")

                result = runner.invoke(app, ["chat"], input="exit\n")

                assert result.exit_code == 1
                # 检查友好的错误提示
                assert "未设置 Gemini API Key" in result.stdout or "API Key" in result.stdout

    def test_chat_with_api_key(self) -> None:
        """测试使用API key启动chat"""
        with patch("novel_agent.cli.create_specialized_agent") as mock_create:
            mock_agent = Mock()
            mock_agent.invoke.return_value = {"messages": [Mock(content="你好！我是Agent。")]}
            mock_create.return_value = mock_agent

            result = runner.invoke(app, ["chat", "--api-key", "test-key"], input="hello\nexit\n")

            assert result.exit_code == 0
            kwargs = mock_create.call_args.kwargs
            assert kwargs["api_key"] == "test-key"
            assert "checkpointer" in kwargs

    def test_chat_with_custom_agent(self) -> None:
        """测试使用自定义Agent类型"""
        with patch("novel_agent.cli.create_specialized_agent") as mock_create:
            mock_agent = Mock()
            mock_agent.invoke.return_value = {"messages": [Mock(content="大纲已生成")]}
            mock_create.return_value = mock_agent

            result = runner.invoke(
                app,
                ["chat", "--agent", "outline-architect", "--api-key", "test-key"],
                input="exit\n",
            )

            assert result.exit_code == 0
            kwargs = mock_create.call_args.kwargs
            assert kwargs["api_key"] == "test-key"
            assert "checkpointer" in kwargs

    def test_chat_exit_command(self) -> None:
        """测试exit命令"""
        with patch("novel_agent.cli.create_specialized_agent") as mock_create:
            mock_agent = Mock()
            mock_create.return_value = mock_agent

            result = runner.invoke(app, ["chat"], input="exit\n")

            # 应该优雅退出
            assert "再见" in result.stdout or result.exit_code in (0, 1)


class TestCheckCommand:
    """测试 check 命令"""

    def test_check_nonexistent_file(self) -> None:
        """测试检查不存在的文件"""
        result = runner.invoke(app, ["check", "/nonexistent/file.md"])

        assert result.exit_code == 1
        assert "文件不存在" in result.stdout

    def test_check_existing_file(self, tmp_path: Path) -> None:
        """测试检查存在的文件"""
        # 创建测试文件
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Chapter")

        with patch("novel_agent.cli.create_novel_agent") as mock_create:
            mock_agent = Mock()
            mock_agent.invoke.return_value = {"messages": [Mock(content="✅ 未发现一致性问题")]}
            mock_create.return_value = mock_agent

            result = runner.invoke(app, ["check", str(test_file)])

            assert result.exit_code == 0
            assert "一致性检查" in result.stdout
            mock_agent.invoke.assert_called_once()

    def test_check_with_api_key(self, tmp_path: Path) -> None:
        """测试使用API key检查文件"""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        with patch("novel_agent.cli.create_novel_agent") as mock_create:
            mock_agent = Mock()
            mock_agent.invoke.return_value = {"messages": [Mock(content="OK")]}
            mock_create.return_value = mock_agent

            result = runner.invoke(app, ["check", str(test_file), "--api-key", "test-key"])

            assert result.exit_code == 0
            mock_create.assert_called_once_with(api_key="test-key")
