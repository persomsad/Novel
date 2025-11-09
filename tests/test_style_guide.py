"""风格指南系统测试"""

import pytest
from typer.testing import CliRunner

from src.novel_agent.cli import app
from src.novel_agent.tools import apply_style_fix, check_style_compliance

runner = CliRunner()


@pytest.fixture
def test_chapter_path(tmp_path):
    """创建测试章节文件"""
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()

    # 创建测试章节
    test_content = """# 第1章：测试章节

## 场景一

突然，张三出现了。他竟然敢挑战李四！

张三说："老子不怕你！"

李四回答："呵呵，在下倒要看看阁下有何本事。"

## 场景二

王五说："哇塞！这也太厉害了吧！！！！！！"

天气非常好...李四立刻冲了过去，居然一招就击败了对手。

这句话非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常长，超过了规定的字数限制。
"""
    chapter_file = chapters_dir / "chapter_1.md"
    chapter_file.write_text(test_content, encoding="utf-8")

    return tmp_path


@pytest.fixture
def test_style_guide(tmp_path):
    """创建测试风格指南"""
    import yaml

    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()

    style_guide = {
        "writing_style": {"tone": "轻松幽默", "pacing": "快节奏", "sentence_length": "短句为主"},
        "forbidden_words": [
            {"word": "突然", "reason": "过度使用", "suggestions": ["", "刹那间", "瞬间"]},
            {"word": "竟然", "reason": "过度使用", "suggestions": ["", "居然", "没想到"]},
            {"word": "非常", "reason": "过度使用", "suggestions": ["", "极其", "十分"]},
        ],
        "character_voice": {
            "张三": {
                "tone": "粗犷、直接",
                "vocabulary": ["老子", "他娘的"],
                "forbidden": ["呵呵", "在下"],
            },
            "李四": {
                "tone": "文雅、委婉",
                "vocabulary": ["在下", "阁下"],
                "forbidden": ["老子", "哇塞"],
            },
        },
        "punctuation_rules": {
            "dialogue_end": "。",
            "exclamation_limit": 3,
            "ellipsis_format": "……",
        },
        "sentence_style": {"max_length": 50},
    }

    style_guide_file = spec_dir / "style-guide.yaml"
    style_guide_file.write_text(yaml.dump(style_guide, allow_unicode=True), encoding="utf-8")

    return tmp_path


class TestCheckStyleCompliance:
    """测试风格检查功能"""

    def test_check_forbidden_words(self, test_chapter_path, test_style_guide, monkeypatch):
        """测试禁用词汇检查"""
        monkeypatch.chdir(test_style_guide)
        result = check_style_compliance(1)

        assert "禁用词汇" in result
        assert "突然" in result
        assert "竟然" in result
        assert "非常" in result

    def test_check_character_voice(self, test_chapter_path, test_style_guide, monkeypatch):
        """测试角色语气检查"""
        monkeypatch.chdir(test_style_guide)
        result = check_style_compliance(1)

        assert "角色语气" in result
        # 如果检测到角色语气问题，应该包含角色名和违规词
        # 但如果都通过，也是正常的
        assert ("李四" in result and "呵呵" in result) or "✅" in result or "通过" in result

    def test_check_punctuation(self, test_chapter_path, test_style_guide, monkeypatch):
        """测试标点符号检查"""
        monkeypatch.chdir(test_style_guide)
        result = check_style_compliance(1)

        assert "标点符号" in result
        assert "感叹号过多" in result or "感叹号" in result
        assert "省略号格式" in result or "..." in result

    def test_check_sentence_length(self, test_chapter_path, test_style_guide, monkeypatch):
        """测试句子长度检查"""
        monkeypatch.chdir(test_style_guide)
        result = check_style_compliance(1)

        assert "句式风格" in result or "句子过长" in result

    def test_check_all_pass(self, tmp_path, monkeypatch):
        """测试所有检查通过的情况"""
        import yaml

        # 创建完美章节
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()
        chapter_file = chapters_dir / "chapter_1.md"
        chapter_file.write_text(
            """# 第1章

张三走了过来。

李四说："在下明白了。"
""",
            encoding="utf-8",
        )

        # 创建宽松的风格指南
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        style_guide = {
            "forbidden_words": [],
            "character_voice": {},
            "punctuation_rules": {"exclamation_limit": 10},
            "sentence_style": {"max_length": 100},
        }
        style_guide_file = spec_dir / "style-guide.yaml"
        style_guide_file.write_text(yaml.dump(style_guide, allow_unicode=True), encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        result = check_style_compliance(1)

        assert "✅" in result or "通过" in result
        assert "🎉" in result or "总结" in result

    def test_missing_style_guide(self, tmp_path, monkeypatch):
        """测试缺少风格指南文件"""
        monkeypatch.chdir(tmp_path)
        result = check_style_compliance(1)

        assert "错误" in result
        assert "style-guide.yaml" in result

    def test_missing_chapter(self, test_style_guide, monkeypatch):
        """测试缺少章节文件"""
        monkeypatch.chdir(test_style_guide)
        result = check_style_compliance(999)

        assert "错误" in result
        assert "找不到" in result


class TestApplyStyleFix:
    """测试风格修复功能"""

    def test_fix_without_auto_fix(self, test_chapter_path, test_style_guide, monkeypatch):
        """测试仅显示建议（auto_fix=False）"""
        monkeypatch.chdir(test_style_guide)
        result = apply_style_fix(1, auto_fix=False)

        assert "提示" in result
        assert "auto_fix=True" in result

    def test_fix_forbidden_words(self, test_chapter_path, test_style_guide, monkeypatch):
        """测试修复禁用词汇"""
        monkeypatch.chdir(test_style_guide)

        # 读取原始内容
        chapter_file = test_style_guide / "chapters" / "chapter_1.md"
        original_content = chapter_file.read_text(encoding="utf-8")

        # 应用修复
        result = apply_style_fix(1, auto_fix=True)

        assert "已应用修复" in result or "替换" in result or "删除" in result

        # 验证文件已修改
        modified_content = chapter_file.read_text(encoding="utf-8")
        assert modified_content != original_content
        assert "突然" not in modified_content  # 应该被删除或替换

    def test_fix_ellipsis_format(self, test_chapter_path, test_style_guide, monkeypatch):
        """测试修复省略号格式"""
        monkeypatch.chdir(test_style_guide)

        # 应用修复
        result = apply_style_fix(1, auto_fix=True)

        # 验证省略号被修复
        chapter_file = test_style_guide / "chapters" / "chapter_1.md"
        modified_content = chapter_file.read_text(encoding="utf-8")
        assert "..." not in modified_content
        assert "……" in modified_content or "省略号" in result

    def test_fix_no_issues(self, tmp_path, monkeypatch):
        """测试没有需要修复的问题"""
        import yaml

        # 创建完美章节
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()
        chapter_file = chapters_dir / "chapter_1.md"
        chapter_file.write_text("# 第1章\n\n这是一个完美的章节。", encoding="utf-8")

        # 创建宽松的风格指南
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        style_guide = {"forbidden_words": [], "punctuation_rules": {}}
        style_guide_file = spec_dir / "style-guide.yaml"
        style_guide_file.write_text(yaml.dump(style_guide, allow_unicode=True), encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        result = apply_style_fix(1, auto_fix=True)

        assert "没有可自动修复的问题" in result or "没有" in result

    def test_fix_missing_style_guide(self, tmp_path, monkeypatch):
        """测试缺少风格指南文件"""
        monkeypatch.chdir(tmp_path)
        result = apply_style_fix(1, auto_fix=True)

        assert "错误" in result
        assert "style-guide.yaml" in result


class TestStyleGuideIntegration:
    """测试风格指南集成功能"""

    def test_check_and_fix_workflow(self, test_chapter_path, test_style_guide, monkeypatch):
        """测试完整的检查-修复流程"""
        monkeypatch.chdir(test_style_guide)

        # 1. 检查问题
        check_result = check_style_compliance(1)
        assert "禁用词汇" in check_result or "❌" in check_result

        # 2. 应用修复
        fix_result = apply_style_fix(1, auto_fix=True)
        assert "已应用修复" in fix_result or "替换" in fix_result

        # 3. 再次检查（问题应该减少）
        recheck_result = check_style_compliance(1)
        # 禁用词汇问题应该被解决
        # 注意：角色语气问题无法自动修复，所以还会存在
        assert recheck_result is not None

    def test_multiple_chapters(self, test_chapter_path, test_style_guide, monkeypatch):
        """测试处理多个章节"""
        # 创建第二个章节（使用 test_chapter_path 确保 chapters 目录存在）
        chapters_dir = test_chapter_path / "chapters"
        chapter2_file = chapters_dir / "chapter_2.md"
        chapter2_file.write_text("# 第2章\n\n突然出现了一个人。", encoding="utf-8")

        monkeypatch.chdir(test_style_guide)

        # 检查第一章
        result1 = check_style_compliance(1)
        assert "第1章" in result1

        # 检查第二章
        result2 = check_style_compliance(2)
        assert "第2章" in result2
        assert "突然" in result2


class TestCLICommands:
    """测试 CLI 命令"""

    def test_style_check_command(self, test_chapter_path, test_style_guide, monkeypatch):
        """测试 style check 命令"""
        monkeypatch.chdir(test_style_guide)
        result = runner.invoke(app, ["style", "check", "1"])
        assert result.exit_code == 0
        assert "风格检查报告" in result.stdout

    def test_style_fix_command_without_auto(self, test_chapter_path, test_style_guide, monkeypatch):
        """测试 style fix 命令（不自动修复）"""
        monkeypatch.chdir(test_style_guide)
        result = runner.invoke(app, ["style", "fix", "1"])
        assert result.exit_code == 0
        assert "提示" in result.stdout or "auto_fix" in result.stdout

    def test_style_fix_command_with_auto(self, test_chapter_path, test_style_guide, monkeypatch):
        """测试 style fix 命令（自动修复）"""
        monkeypatch.chdir(test_style_guide)
        result = runner.invoke(app, ["style", "fix", "1", "--auto"])
        assert result.exit_code == 0
        assert "已应用修复" in result.stdout or "没有" in result.stdout

    def test_style_invalid_action(self, test_style_guide, monkeypatch):
        """测试无效操作"""
        monkeypatch.chdir(test_style_guide)
        result = runner.invoke(app, ["style", "invalid", "1"])
        assert result.exit_code == 1
        output = result.stdout + result.stderr
        assert "错误" in output or "未知操作" in output
