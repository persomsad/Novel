"""批量检查功能测试"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from novel_agent.cli import app

runner = CliRunner()


class TestBatchCheck:
    """测试批量检查功能"""

    @patch("novel_agent.cli.create_novel_agent")
    def test_batch_check_multiple_files(self, mock_create_agent: MagicMock) -> None:
        """测试批量检查多个文件

        验收标准：
        - 支持 glob 模式匹配多个文件
        - 显示进度条
        - 生成汇总报告
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建多个测试文件
            tmppath = Path(tmpdir)
            (tmppath / "ch001.md").write_text("# 第一章\n\n正常内容。")
            (tmppath / "ch002.md").write_text("# 第二章\n\n正常内容。")
            (tmppath / "ch003.md").write_text("# 第三章\n\n有问题的内容。")

            # Mock agent响应
            mock_agent = MagicMock()

            def mock_invoke(input_data: dict, config: dict) -> dict:
                # 根据文件名返回不同结果
                thread_id = config["configurable"]["thread_id"]
                if "ch003" in thread_id:
                    return {"messages": [MagicMock(content="- Line 5: 时间线错误（前后矛盾）")]}
                return {"messages": [MagicMock(content="通过")]}

            mock_agent.invoke.side_effect = mock_invoke
            mock_create_agent.return_value = mock_agent

            # 执行批量检查
            result = runner.invoke(
                app,
                ["check", f"{tmpdir}/ch*.md", "--api-key", "test-key"],
            )

            # 验证命令成功
            assert result.exit_code == 0

            # 验证汇总报告
            assert "汇总报告" in result.stdout
            assert "通过: 2" in result.stdout
            assert "警告: 1" in result.stdout or "错误:" in result.stdout

    @patch("novel_agent.cli.create_novel_agent")
    def test_batch_check_json_output(self, mock_create_agent: MagicMock) -> None:
        """测试批量检查的 JSON 输出格式

        验收标准：
        - 支持 --output-format json
        - 返回结构化的 JSON 数据
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            tmppath = Path(tmpdir)
            (tmppath / "ch001.md").write_text("# 第一章")
            (tmppath / "ch002.md").write_text("# 第二章")

            # Mock agent响应
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = {"messages": [MagicMock(content="通过")]}
            mock_create_agent.return_value = mock_agent

            # 执行批量检查
            result = runner.invoke(
                app,
                [
                    "check",
                    f"{tmpdir}/ch*.md",
                    "--api-key",
                    "test-key",
                    "--output-format",
                    "json",
                ],
            )

            # 验证命令成功
            assert result.exit_code == 0

            # 验证 JSON 输出
            import json

            output = json.loads(result.stdout)
            assert "total_files" in output
            assert "passed" in output
            assert "results" in output
            assert output["total_files"] == 2

    @patch("novel_agent.cli.create_novel_agent")
    def test_batch_check_parallel(self, mock_create_agent: MagicMock) -> None:
        """测试并行批量检查

        验收标准：
        - 支持 --parallel 参数
        - 能够并行处理多个文件
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建多个测试文件
            tmppath = Path(tmpdir)
            for i in range(5):
                (tmppath / f"ch{i:03d}.md").write_text(f"# 第{i+1}章")

            # Mock agent响应
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = {"messages": [MagicMock(content="通过")]}
            mock_create_agent.return_value = mock_agent

            # 执行并行批量检查
            result = runner.invoke(
                app,
                ["check", f"{tmpdir}/ch*.md", "--api-key", "test-key", "--parallel"],
            )

            # 验证命令成功
            assert result.exit_code == 0

            # 验证汇总报告
            assert "汇总报告" in result.stdout
            assert "通过: 5" in result.stdout

            # 验证 agent 被调用了 5 次
            assert mock_agent.invoke.call_count == 5

    @patch("novel_agent.cli.create_novel_agent")
    def test_batch_check_auto_fix(self, mock_create_agent: MagicMock) -> None:
        """测试自动修复参数

        验收标准：
        - 支持 --auto-fix 参数
        - 传递正确的参数给检查函数
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            tmppath = Path(tmpdir)
            (tmppath / "ch001.md").write_text("# 第一章")

            # Mock agent响应
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = {"messages": [MagicMock(content="通过")]}
            mock_create_agent.return_value = mock_agent

            # 执行自动修复检查
            result = runner.invoke(
                app,
                ["check", f"{tmpdir}/ch*.md", "--api-key", "test-key", "--auto-fix"],
            )

            # 验证命令成功
            assert result.exit_code == 0

            # 验证 agent 被调用时包含修复提示
            call_args = mock_agent.invoke.call_args_list[0]
            prompt = call_args[0][0]["messages"][0][1]
            assert "修复" in prompt

    @patch("novel_agent.cli.create_novel_agent")
    def test_batch_check_no_files_found(self, mock_create_agent: MagicMock) -> None:
        """测试找不到匹配文件的情况

        验收标准：
        - 当 glob 模式不匹配任何文件时
        - 返回错误信息
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # 不创建任何文件，直接尝试匹配
            result = runner.invoke(
                app,
                ["check", f"{tmpdir}/nonexistent*.md", "--api-key", "test-key"],
            )

            # 验证命令失败
            assert result.exit_code == 1

            # 验证错误信息
            assert "没有找到匹配的文件" in result.stdout

    @patch("novel_agent.cli.create_novel_agent")
    def test_single_file_backward_compatibility(self, mock_create_agent: MagicMock) -> None:
        """测试单文件模式的向后兼容性

        验收标准：
        - 单个文件仍然使用原来的显示格式
        - 不显示批量检查的汇总报告
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建单个测试文件
            test_file = Path(tmpdir) / "ch001.md"
            test_file.write_text("# 第一章")

            # Mock agent响应
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = {"messages": [MagicMock(content="通过")]}
            mock_create_agent.return_value = mock_agent

            # 执行单文件检查（不使用 glob）
            result = runner.invoke(
                app,
                ["check", str(test_file), "--api-key", "test-key"],
            )

            # 验证命令成功
            assert result.exit_code == 0

            # 验证使用单文件格式（不显示汇总报告）
            assert "汇总报告" not in result.stdout
            assert "一致性检查" in result.stdout

    @patch("novel_agent.cli.create_novel_agent")
    def test_batch_check_with_errors(self, mock_create_agent: MagicMock) -> None:
        """测试批量检查时发现错误的情况

        验收标准：
        - 正确统计错误和警告
        - 显示详细的问题列表
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            tmppath = Path(tmpdir)
            (tmppath / "ch001.md").write_text("# 第一章")
            (tmppath / "ch002.md").write_text("# 第二章")
            (tmppath / "ch003.md").write_text("# 第三章")

            # Mock agent响应
            mock_agent = MagicMock()

            def mock_invoke(input_data: dict, config: dict) -> dict:
                thread_id = config["configurable"]["thread_id"]
                if "ch001" in thread_id:
                    return {"messages": [MagicMock(content="- Line 5: 严重错误：时间线崩溃")]}
                elif "ch002" in thread_id:
                    return {"messages": [MagicMock(content="- Line 10: 轻微问题：用词不当")]}
                return {"messages": [MagicMock(content="通过")]}

            mock_agent.invoke.side_effect = mock_invoke
            mock_create_agent.return_value = mock_agent

            # 执行批量检查
            result = runner.invoke(
                app,
                ["check", f"{tmpdir}/ch*.md", "--api-key", "test-key"],
            )

            # 验证命令成功
            assert result.exit_code == 0

            # 验证汇总报告包含正确的统计
            assert "通过: 1" in result.stdout
            assert "错误: 1" in result.stdout or "警告: 2" in result.stdout

            # 验证显示详细问题
            assert "详细信息" in result.stdout
