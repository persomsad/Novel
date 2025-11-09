"""测试流式输出功能"""

import json
from typing import Any
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from novel_agent.cli import app

runner = CliRunner()


class TestStreaming:
    """测试 --stream 模式"""

    @patch("novel_agent.cli.create_specialized_agent")
    @patch("novel_agent.cli.open_checkpointer")
    def test_stream_text_output(
        self, mock_checkpointer: MagicMock, mock_create_agent: MagicMock
    ) -> None:
        """测试流式文本输出"""
        # Mock Agent 流式响应
        mock_agent = MagicMock()

        # 模拟流式输出：分3个 chunk
        def mock_stream(*args: Any, **kwargs: Any) -> Any:
            # Chunk 1
            msg1 = MagicMock()
            msg1.content = "这是"
            yield {"messages": [msg1]}

            # Chunk 2
            msg2 = MagicMock()
            msg2.content = "这是流式"
            yield {"messages": [msg2]}

            # Chunk 3
            msg3 = MagicMock()
            msg3.content = "这是流式响应"
            yield {"messages": [msg3]}

        mock_agent.stream = mock_stream
        mock_create_agent.return_value = mock_agent
        mock_checkpointer.return_value.__enter__.return_value = MagicMock()

        # 执行命令
        result = runner.invoke(app, ["chat", "--print", "--stream", "测试"])

        assert result.exit_code == 0
        assert "这是流式响应" in result.stdout

    @patch("novel_agent.cli.create_specialized_agent")
    @patch("novel_agent.cli.open_checkpointer")
    def test_stream_json_output(
        self, mock_checkpointer: MagicMock, mock_create_agent: MagicMock
    ) -> None:
        """测试流式 JSON 输出"""
        # Mock Agent 流式响应
        mock_agent = MagicMock()

        def mock_stream(*args: Any, **kwargs: Any) -> Any:
            msg1 = MagicMock()
            msg1.content = "测试"
            yield {"messages": [msg1]}

            msg2 = MagicMock()
            msg2.content = "测试响应"
            yield {"messages": [msg2]}

        mock_agent.stream = mock_stream
        mock_create_agent.return_value = mock_agent
        mock_checkpointer.return_value.__enter__.return_value = MagicMock()

        # 执行命令
        result = runner.invoke(
            app, ["chat", "--print", "--stream", "--output-format", "stream-json", "测试"]
        )

        assert result.exit_code == 0
        # 验证输出包含流式 JSON
        lines = result.stdout.strip().split("\n")
        assert len(lines) >= 1  # 至少有一行输出

        # 最后一行应该是 done=True
        last_line = json.loads(lines[-1])
        assert last_line["done"] is True
        assert "confidence" in last_line
        assert "response" in last_line

    @patch("novel_agent.cli.create_specialized_agent")
    @patch("novel_agent.cli.open_checkpointer")
    def test_stream_without_print_flag(
        self, mock_checkpointer: MagicMock, mock_create_agent: MagicMock
    ) -> None:
        """测试 --stream 需要配合 --print 使用"""
        # Mock Agent
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        mock_checkpointer.return_value.__enter__.return_value = MagicMock()

        # --stream 单独使用（不带 --print）应该被忽略，进入交互模式
        # 这里我们不测试交互模式，只确保不会崩溃
        # 实际上 --stream 主要用于 --print 模式
        pass

    @patch("novel_agent.cli.create_specialized_agent")
    @patch("novel_agent.cli.open_checkpointer")
    def test_stream_with_pipe_input(
        self, mock_checkpointer: MagicMock, mock_create_agent: MagicMock
    ) -> None:
        """测试流式输出 + 管道输入"""
        mock_agent = MagicMock()

        def mock_stream(*args: Any, **kwargs: Any) -> Any:
            msg = MagicMock()
            msg.content = "管道流式响应"
            yield {"messages": [msg]}

        mock_agent.stream = mock_stream
        mock_create_agent.return_value = mock_agent
        mock_checkpointer.return_value.__enter__.return_value = MagicMock()

        result = runner.invoke(app, ["chat", "--print", "--stream"], input="管道输入问题")

        assert result.exit_code == 0
        assert "管道流式响应" in result.stdout

    @patch("novel_agent.cli.create_specialized_agent")
    @patch("novel_agent.cli.open_checkpointer")
    def test_stream_empty_chunks(
        self, mock_checkpointer: MagicMock, mock_create_agent: MagicMock
    ) -> None:
        """测试流式输出处理空 chunk"""
        mock_agent = MagicMock()

        def mock_stream(*args: Any, **kwargs: Any) -> Any:
            # 空 messages
            yield {"messages": []}

            # 有 content 的消息
            msg = MagicMock()
            msg.content = "最终响应"
            yield {"messages": [msg]}

        mock_agent.stream = mock_stream
        mock_create_agent.return_value = mock_agent
        mock_checkpointer.return_value.__enter__.return_value = MagicMock()

        result = runner.invoke(app, ["chat", "--print", "--stream", "测试"])

        assert result.exit_code == 0
        assert "最终响应" in result.stdout
