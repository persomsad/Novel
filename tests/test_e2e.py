"""End-to-End Tests

测试完整的用户交互流程
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from novel_agent.cli import app

runner = CliRunner()


class TestE2ECheckCommand:
    """测试端到端check命令流程（核心功能）"""

    @patch("novel_agent.cli.create_novel_agent")
    def test_check_command_e2e(self, mock_create_agent: MagicMock) -> None:
        """测试check命令的完整端到端流程

        验收标准：
        - 用户启动CLI check命令
        - Agent分析章节内容
        - 用户收到检查结果
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试章节
            test_chapter = Path(tmpdir) / "ch001.md"
            test_chapter.write_text("# 第一章\n\n李明走进咖啡馆。")

            # Mock agent响应
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = {
                "messages": [MagicMock(content="✅ 章节内容正常，没有发现一致性问题。")]
            }
            mock_create_agent.return_value = mock_agent

            # 执行check命令
            result = runner.invoke(
                app,
                ["check", str(test_chapter), "--api-key", "test-key"],
            )

            # 验证命令成功
            assert result.exit_code == 0

            # 验证输出包含检查结果
            assert "章节内容正常" in result.stdout or "检查结果" in result.stdout

            # 验证agent被正确调用
            assert mock_create_agent.called
            assert mock_agent.invoke.called

    @patch("novel_agent.cli.create_novel_agent")
    def test_check_command_with_issues(self, mock_create_agent: MagicMock) -> None:
        """测试check命令发现问题的场景

        验收标准：
        - Agent检测到一致性问题
        - 用户收到问题报告
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建有问题的章节
            test_chapter = Path(tmpdir) / "ch002.md"
            test_chapter.write_text(
                """# 第二章

李明是个内向的人。
但今天他主动邀请了20个朋友开派对。
"""
            )

            # Mock agent发现问题
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = {
                "messages": [MagicMock(content="⚠️ 发现角色一致性问题：李明的性格前后矛盾")]
            }
            mock_create_agent.return_value = mock_agent

            # 执行check命令
            result = runner.invoke(
                app,
                ["check", str(test_chapter), "--api-key", "test-key"],
            )

            # 验证命令成功
            assert result.exit_code == 0

            # 验证输出包含问题报告
            assert "角色一致性问题" in result.stdout or "检查结果" in result.stdout


class TestE2ECreateChapter:
    """测试端到端章节创作流程"""

    def test_write_chapter_tool_e2e(self) -> None:
        """测试write_chapter工具的端到端流程

        验收标准：
        - 创建章节文件
        - 文件包含正确内容
        - 返回文件路径
        """
        from novel_agent.tools import write_chapter

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建章节
            content = "# 第一章\n\n李明走进咖啡馆。"
            file_path = write_chapter(1, content, base_dir=tmpdir)

            # 验证文件创建
            assert Path(file_path).exists()

            # 验证文件内容
            assert Path(file_path).read_text() == content

            # 验证文件命名格式
            assert "ch001.md" in file_path


class TestE2ESearchContent:
    """测试端到端搜索功能"""

    def test_search_content_e2e(self) -> None:
        """测试search_content的端到端流程

        验收标准：
        - 在测试数据中搜索关键词
        - 返回匹配结果
        """
        from novel_agent.tools import search_content

        # 搜索测试数据中的角色
        results = search_content("李明", "spec/knowledge")

        # 验证找到结果
        assert len(results) > 0

        # 验证结果格式
        assert "file" in results[0]
        assert "line" in results[0]
        assert "content" in results[0]


class TestE2EIntegration:
    """真实API集成测试（需要手动启用）"""

    @pytest.mark.skip(reason="需要真实的Gemini API key，手动测试时启用")
    def test_real_check_command(self) -> None:
        """使用真实API测试check命令

        运行方式：
        export GOOGLE_API_KEY=your-key
        pytest tests/test_e2e.py::TestE2EIntegration::test_real_check_command -v -s
        """
        import os

        if not os.getenv("GOOGLE_API_KEY"):
            pytest.skip("需要GOOGLE_API_KEY环境变量")

        # 使用真实的章节文件
        result = runner.invoke(app, ["check", "chapters/ch001.md"])

        assert result.exit_code == 0
        print("\n=== 检查结果 ===")
        print(result.stdout)
