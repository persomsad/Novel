"""写作模板系统测试"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from src.novel_agent.cli import app
from src.novel_agent.tools import apply_template, list_templates

runner = CliRunner()


class TestListTemplates:
    """测试模板列表功能"""

    def test_list_all_templates(self):
        """测试列出所有模板"""
        result = list_templates()
        assert "可用的写作模板" in result
        assert "scene-description" in result
        assert "dialogue" in result
        assert "action" in result
        assert "psychology" in result
        assert "transition" in result

    def test_list_templates_by_category(self):
        """测试按分类列出模板"""
        # 场景类模板
        result = list_templates(category="scene")
        assert "scene-description" in result
        assert "dialogue" not in result

        # 对话类模板
        result = list_templates(category="dialogue")
        assert "dialogue" in result
        assert "scene-description" not in result

    def test_list_templates_invalid_category(self):
        """测试无效分类"""
        result = list_templates(category="invalid")
        assert "未找到分类为 'invalid' 的模板" in result


class TestApplyTemplate:
    """测试模板应用功能"""

    def test_apply_scene_template(self):
        """测试应用场景描写模板"""
        result = apply_template(
            "scene-description",
            {
                "time": "黄昏",
                "location": "荒凉的战场上",
                "weather": "乌云密布",
                "details": "残破的旗帜在风中猎猎作响。",
                "atmosphere": "肃杀",
            },
        )
        assert "黄昏" in result
        assert "荒凉的战场上" in result
        assert "乌云密布" in result
        assert "肃杀" in result
        assert "${" not in result  # 所有变量都应被替换

    def test_apply_dialogue_template(self):
        """测试应用对话模板"""
        result = apply_template(
            "dialogue",
            {
                "character": "张三",
                "emotion": "愤怒",
                "action": "猛地一拍桌子",
                "expression": "双目圆睁",
                "dialogue": "你竟敢欺骗我！",
                "psychology": "他心中怒火中烧。",
            },
        )
        assert "张三" in result
        assert "愤怒" in result
        assert "你竟敢欺骗我！" in result
        assert "${" not in result

    def test_apply_action_template(self):
        """测试应用动作描写模板"""
        result = apply_template(
            "action",
            {
                "character_a": "张三",
                "character_b": "李四",
                "action_a": "剑光如电般刺向对方",
                "action_b": "险险侧身躲过",
                "result": "剑气擦过李四的面颊。",
                "impact": "围观众人倒吸一口凉气！",
            },
        )
        assert "张三" in result
        assert "李四" in result
        assert "剑气擦过李四的面颊" in result
        assert "${" not in result

    def test_apply_psychology_template(self):
        """测试应用心理描写模板"""
        result = apply_template(
            "psychology",
            {
                "character": "张三",
                "trigger": "看着师父的遗物",
                "emotion": "悲痛交加",
                "thought": "师父，我一定会为您报仇！",
                "decision": "他紧紧握住手中的令牌。",
            },
        )
        assert "张三" in result
        assert "师父的遗物" in result
        assert "悲痛交加" in result
        assert "${" not in result

    def test_apply_transition_template(self):
        """测试应用场景过渡模板"""
        # 时间过渡
        result = apply_template(
            "transition",
            {
                "transition_type": "time",
                "time_gap": "三天后",
                "from_location": "",
                "to_location": "",
                "character": "",
                "activity": "张三完成了闭关修炼",
            },
        )
        assert "三天后" in result

        # 空间过渡
        result = apply_template(
            "transition",
            {
                "transition_type": "space",
                "time_gap": "",
                "from_location": "城主府",
                "to_location": "张家后院",
                "character": "张三",
                "activity": "穿过繁华的街市",
            },
        )
        assert "城主府" in result
        assert "张家后院" in result

    def test_apply_template_missing_variables(self):
        """测试缺少必需变量"""
        result = apply_template(
            "scene-description",
            {
                "time": "黄昏",
                # 缺少其他变量
            },
        )
        assert "黄昏" in result
        # 应该包含未提供值的变量警告
        assert ("${" in result) or ("未提供值" in result)

    def test_apply_template_not_found(self):
        """测试模板不存在"""
        result = apply_template("nonexistent", {})
        assert "❌" in result
        assert "不存在" in result
        # 应该列出可用模板
        assert "可用的写作模板" in result


class TestTemplateIntegration:
    """集成测试"""

    def test_list_then_apply(self):
        """测试先列出模板，再应用"""
        # 1. 列出所有模板
        templates = list_templates()
        assert "scene-description" in templates

        # 2. 应用其中一个模板
        result = apply_template(
            "scene-description",
            {
                "time": "午夜",
                "location": "密林深处",
                "weather": "月色如水",
                "details": "树影婆娑，虫鸣声声。",
                "atmosphere": "神秘而宁静",
            },
        )
        assert "午夜" in result
        assert "密林深处" in result

    def test_all_templates_can_be_applied(self):
        """测试所有模板都能正常应用"""
        templates_dir = Path("spec/templates")
        if not templates_dir.exists():
            pytest.skip("模板目录不存在")

        template_files = list(templates_dir.glob("*.md"))
        assert len(template_files) > 0, "至少应该有一个模板"

        for template_file in template_files:
            template_name = template_file.stem
            # 使用空变量字典测试（会有警告，但不应报错）
            result = apply_template(template_name, {})
            assert isinstance(result, str)
            assert len(result) > 0


class TestCLICommands:
    """测试 CLI 命令"""

    def test_template_list_command(self):
        """测试 template list 命令"""
        result = runner.invoke(app, ["template", "list"])
        assert result.exit_code == 0
        assert "可用的写作模板" in result.stdout
        assert "scene-description" in result.stdout

    def test_template_list_with_category(self):
        """测试 template list 带分类过滤"""
        result = runner.invoke(app, ["template", "list", "--category", "scene"])
        assert result.exit_code == 0
        assert "scene-description" in result.stdout

    def test_template_apply_command(self):
        """测试 template apply 命令"""
        result = runner.invoke(
            app,
            [
                "template",
                "apply",
                "--name",
                "scene-description",
                "--var",
                "time=黄昏",
                "--var",
                "location=战场",
                "--var",
                "weather=乌云密布",
                "--var",
                "details=残旗飘扬",
                "--var",
                "atmosphere=肃杀",
            ],
        )
        assert result.exit_code == 0
        assert "黄昏" in result.stdout
        assert "战场" in result.stdout

    def test_template_apply_without_name(self):
        """测试 apply 缺少 name 参数"""
        result = runner.invoke(app, ["template", "apply"])
        assert result.exit_code == 1
        output = result.stdout + result.stderr
        assert "错误" in output or "需要" in output

    def test_template_invalid_action(self):
        """测试无效操作"""
        result = runner.invoke(app, ["template", "invalid"])
        assert result.exit_code == 1
        output = result.stdout + result.stderr
        assert "未知操作" in output or "错误" in output
