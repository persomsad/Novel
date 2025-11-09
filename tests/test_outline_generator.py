"""大纲生成器测试"""

from typer.testing import CliRunner

from src.novel_agent.cli import app
from src.novel_agent.tools import generate_outline

runner = CliRunner()


class TestGenerateOutline:
    """测试大纲生成功能"""

    def test_generate_basic_outline(self):
        """测试基本大纲生成"""
        result = generate_outline(
            genre="玄幻", target_words=100000, themes=["复仇", "成长"], style="爽文"
        )

        assert "玄幻小说大纲" in result
        assert "100000字" in result
        assert "复仇" in result
        assert "成长" in result
        assert "第一幕" in result
        assert "第二幕" in result
        assert "第三幕" in result

    def test_generate_different_genres(self):
        """测试不同题材"""
        genres = ["玄幻", "都市", "科幻", "武侠", "历史", "言情"]

        for genre in genres:
            result = generate_outline(
                genre=genre, target_words=50000, themes=["成长"], style="爽文"
            )
            assert genre in result
            assert "50000字" in result

    def test_generate_different_styles(self):
        """测试不同风格"""
        styles = ["爽文", "虐文", "轻松", "严肃"]

        for style in styles:
            result = generate_outline(
                genre="玄幻", target_words=100000, themes=["成长"], style=style
            )
            assert style in result

    def test_generate_multiple_themes(self):
        """测试多个主题"""
        themes = ["复仇", "成长", "爱情", "友情"]
        result = generate_outline(genre="都市", target_words=80000, themes=themes, style="轻松")

        for theme in themes:
            assert theme in result

    def test_generate_small_novel(self):
        """测试小型小说（少于10章）"""
        result = generate_outline(genre="短篇", target_words=5000, themes=["悬疑"], style="严肃")

        assert "小说大纲" in result
        # 最少10章
        assert "10章" in result

    def test_generate_large_novel(self):
        """测试大型小说"""
        result = generate_outline(
            genre="玄幻", target_words=500000, themes=["修仙", "热血"], style="爽文"
        )

        assert "500000字" in result
        assert "500章" in result

    def test_three_act_structure(self):
        """测试三幕结构正确性"""
        result = generate_outline(genre="玄幻", target_words=100000, themes=["成长"], style="爽文")

        # 验证三幕都存在
        assert "第一幕" in result
        assert "第二幕" in result
        assert "第三幕" in result

        # 验证角色成长弧线
        assert "角色成长弧线" in result
        assert "起点" in result
        assert "终点" in result


class TestCLICommands:
    """测试 CLI 命令"""

    def test_outline_generate_command(self):
        """测试 outline generate 命令"""
        result = runner.invoke(
            app,
            [
                "outline",
                "generate",
                "--genre",
                "玄幻",
                "--target-words",
                "100000",
                "--themes",
                "复仇,成长",
                "--style",
                "爽文",
            ],
        )

        assert result.exit_code == 0
        assert "玄幻小说大纲" in result.stdout
        assert "100000字" in result.stdout

    def test_outline_generate_with_output(self, tmp_path):
        """测试带输出文件的命令"""
        output_file = tmp_path / "outline.md"

        result = runner.invoke(
            app,
            [
                "outline",
                "generate",
                "-g",
                "都市",
                "-w",
                "50000",
                "-t",
                "爱情,职场",
                "-s",
                "轻松",
                "-o",
                str(output_file),
            ],
        )

        assert result.exit_code == 0
        assert "已保存到" in result.stdout
        assert output_file.exists()

        content = output_file.read_text(encoding="utf-8")
        assert "都市小说大纲" in content
        assert "50000字" in content

    def test_outline_missing_parameters(self):
        """测试缺少必需参数"""
        # 缺少 genre
        result = runner.invoke(
            app,
            [
                "outline",
                "generate",
                "--target-words",
                "100000",
                "--themes",
                "成长",
            ],
        )
        assert result.exit_code == 1
        output = result.stdout + result.stderr
        assert "错误" in output or "缺少" in output

    def test_outline_invalid_action(self):
        """测试无效操作"""
        result = runner.invoke(
            app,
            [
                "outline",
                "invalid",
                "--genre",
                "玄幻",
                "--target-words",
                "100000",
                "--themes",
                "成长",
            ],
        )
        assert result.exit_code == 1
        output = result.stdout + result.stderr
        assert "错误" in output or "未知操作" in output
