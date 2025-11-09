"""测试非交互模式（--print）功能"""

import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from novel_agent.cli import app

runner = CliRunner()


class TestPrintMode:
    """测试 --print 模式"""

    @patch("novel_agent.cli.create_specialized_agent")
    @patch("novel_agent.cli.open_checkpointer")
    def test_print_mode_with_prompt_text_output(self, mock_checkpointer, mock_create_agent) -> None:
        """测试 --print 模式 + 文本输出"""
        # Mock Agent 响应
        mock_agent = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "这是测试响应"
        mock_agent.invoke.return_value = {"messages": [mock_message]}
        mock_create_agent.return_value = mock_agent
        mock_checkpointer.return_value.__enter__.return_value = MagicMock()

        # 执行命令
        result = runner.invoke(app, ["chat", "--print", "测试问题"])

        assert result.exit_code == 0
        assert "这是测试响应" in result.stdout

    @patch("novel_agent.cli.create_specialized_agent")
    @patch("novel_agent.cli.open_checkpointer")
    def test_print_mode_with_json_output(self, mock_checkpointer, mock_create_agent) -> None:
        """测试 --print --output-format json"""
        # Mock Agent 响应
        mock_agent = MagicMock()
        mock_message = MagicMock()
        mock_message.type = "ai"
        mock_message.content = "这是JSON响应"
        mock_agent.invoke.return_value = {"messages": [mock_message]}
        mock_create_agent.return_value = mock_agent
        mock_checkpointer.return_value.__enter__.return_value = MagicMock()

        # 执行命令
        result = runner.invoke(app, ["chat", "--print", "--output-format", "json", "测试问题"])

        assert result.exit_code == 0
        # 验证 JSON 输出
        output = json.loads(result.stdout)
        assert "response" in output
        assert "confidence" in output
        assert "messages" in output
        assert output["response"] == "这是JSON响应"

    def test_print_mode_without_prompt(self) -> None:
        """测试 --print 模式缺少提示词"""
        result = runner.invoke(app, ["chat", "--print"])

        assert result.exit_code == 1
        assert "错误" in result.stdout or "error" in result.stdout.lower()

    def test_print_mode_invalid_output_format(self) -> None:
        """测试无效的输出格式"""
        result = runner.invoke(app, ["chat", "--print", "--output-format", "invalid", "测试"])

        assert result.exit_code == 1
        assert "无效" in result.stdout or "invalid" in result.stdout.lower()

    @patch("novel_agent.cli.create_specialized_agent")
    @patch("novel_agent.cli.open_checkpointer")
    def test_print_mode_with_pipe_input(self, mock_checkpointer, mock_create_agent) -> None:
        """测试管道输入"""
        # Mock Agent 响应
        mock_agent = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "管道响应"
        mock_agent.invoke.return_value = {"messages": [mock_message]}
        mock_create_agent.return_value = mock_agent
        mock_checkpointer.return_value.__enter__.return_value = MagicMock()

        # 使用 CliRunner 的 input 参数模拟管道输入
        # Note: typer.testing.CliRunner 会自动设置 stdin.isatty()=False
        result = runner.invoke(app, ["chat", "--print"], input="管道输入的问题")

        assert result.exit_code == 0
        assert "管道响应" in result.stdout

    @patch("novel_agent.cli.create_specialized_agent")
    @patch("novel_agent.cli.open_checkpointer")
    def test_print_mode_with_stream_json_format(self, mock_checkpointer, mock_create_agent) -> None:
        """测试 stream-json 格式（暂时等同于 json）"""
        # Mock Agent 响应
        mock_agent = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "流式响应"
        mock_agent.invoke.return_value = {"messages": [mock_message]}
        mock_create_agent.return_value = mock_agent
        mock_checkpointer.return_value.__enter__.return_value = MagicMock()

        # 执行命令
        result = runner.invoke(app, ["chat", "--print", "--output-format", "stream-json", "测试"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert "response" in output
        assert "confidence" in output

    @patch("novel_agent.cli.create_specialized_agent")
    @patch("novel_agent.cli.open_checkpointer")
    def test_print_mode_with_error(self, mock_checkpointer, mock_create_agent) -> None:
        """测试错误处理"""
        # Mock Agent 抛出异常
        mock_agent = MagicMock()
        mock_agent.invoke.side_effect = RuntimeError("测试错误")
        mock_create_agent.return_value = mock_agent
        mock_checkpointer.return_value.__enter__.return_value = MagicMock()

        # 文本格式
        result = runner.invoke(app, ["chat", "--print", "测试"])
        assert result.exit_code == 1

        # JSON 格式
        result = runner.invoke(app, ["chat", "--print", "--output-format", "json", "测试"])
        assert result.exit_code == 1
        output = json.loads(result.stdout)
        assert "error" in output
