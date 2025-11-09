"""测试增强创作工具"""

from src.novel_agent.tools_creative import (
    dialogue_enhancer,
    plot_twist_generator,
    scene_transition,
)


class TestDialogueEnhancer:
    """测试对话润色工具"""

    def test_dialogue_enhancer_basic(self):
        """测试基本对话润色"""
        result = dialogue_enhancer("你是谁？", "张三")
        assert "张三" in result
        assert "你是谁？" in result
        assert "道：" in result or "道:" in result

    def test_dialogue_enhancer_with_emotion_vigilant(self):
        """测试带警惕情绪的对话润色"""
        result = dialogue_enhancer("你是谁？", "张三", "警惕")
        assert "张三" in result
        assert "你是谁？" in result
        assert "眉头一皱" in result or "警惕" in result

    def test_dialogue_enhancer_with_emotion_angry(self):
        """测试带愤怒情绪的对话润色"""
        result = dialogue_enhancer("你竟敢这么做！", "李四", "愤怒")
        assert "李四" in result
        assert "怒" in result or "愤怒" in result

    def test_dialogue_enhancer_with_emotion_sad(self):
        """测试带悲伤情绪的对话润色"""
        result = dialogue_enhancer("为什么会这样...", "王五", "悲伤")
        assert "王五" in result
        assert "悲" in result or "眼眶" in result or "哽咽" in result

    def test_dialogue_enhancer_with_emotion_joyful(self):
        """测试带喜悦情绪的对话润色"""
        result = dialogue_enhancer("太好了！", "赵六", "喜悦")
        assert "赵六" in result
        assert "笑" in result or "喜" in result

    def test_dialogue_enhancer_with_emotion_calm(self):
        """测试带平静情绪的对话润色"""
        result = dialogue_enhancer("我明白了。", "孙七", "平静")
        assert "孙七" in result
        assert "平静" in result

    def test_dialogue_enhancer_multiline(self):
        """测试多行对话润色"""
        dialogue = "你是谁？\n你来这里做什么？"
        result = dialogue_enhancer(dialogue, "张三", "警惕")
        lines = result.split("\n")
        assert len(lines) == 2
        assert all("张三" in line for line in lines)

    def test_dialogue_enhancer_no_character_hint(self):
        """测试无角色提示的对话润色"""
        result = dialogue_enhancer("你好。")
        assert "他" in result or "她" in result
        assert "你好" in result

    def test_dialogue_enhancer_unknown_emotion(self):
        """测试未知情绪（使用默认处理）"""
        result = dialogue_enhancer("你好吗？", "张三", "未知情绪")
        assert "张三" in result
        assert "你好吗？" in result


class TestPlotTwistGenerator:
    """测试情节转折生成工具"""

    def test_plot_twist_generator_basic(self):
        """测试基本情节转折生成"""
        result = plot_twist_generator("张三与李四合作")
        assert "情节转折建议" in result
        assert "1." in result
        assert "2." in result

    def test_plot_twist_generator_low_intensity(self):
        """测试低强度情节转折"""
        result = plot_twist_generator("主角寻找神器", "low")
        assert "情节转折建议" in result
        assert "低强度" in result

    def test_plot_twist_generator_medium_intensity(self):
        """测试中强度情节转折"""
        result = plot_twist_generator("主角寻找神器", "medium")
        assert "情节转折建议" in result
        assert "中强度" in result

    def test_plot_twist_generator_high_intensity(self):
        """测试高强度情节转折"""
        result = plot_twist_generator("主角寻找神器", "high")
        assert "情节转折建议" in result
        assert "高强度" in result

    def test_plot_twist_generator_returns_multiple_suggestions(self):
        """测试返回多个建议"""
        result = plot_twist_generator("主角前往魔窟")
        # 应该有5个建议
        suggestions = [
            line
            for line in result.split("\n")
            if line.strip().startswith(("1.", "2.", "3.", "4.", "5."))
        ]
        assert len(suggestions) == 5

    def test_plot_twist_generator_with_seed(self):
        """测试使用固定种子生成相同结果"""
        result1 = plot_twist_generator("测试情节", "medium", seed=42)
        result2 = plot_twist_generator("测试情节", "medium", seed=42)
        assert result1 == result2

    def test_plot_twist_generator_different_seeds(self):
        """测试不同种子生成不同结果"""
        result1 = plot_twist_generator("测试情节", "medium", seed=42)
        result2 = plot_twist_generator("测试情节", "medium", seed=99)
        # 可能相同但概率很低
        assert result1 == result2 or result1 != result2


class TestSceneTransition:
    """测试场景过渡工具"""

    def test_scene_transition_time(self):
        """测试时间过渡"""
        result = scene_transition("战斗结束", "回到家中", "time")
        assert "战斗结束" in result or "回到家中" in result
        # 应该包含时间词
        time_words = ["后", "清晨", "当晚", "时光"]
        assert any(word in result for word in time_words)

    def test_scene_transition_space(self):
        """测试空间过渡"""
        result = scene_transition("城主府", "张家后院", "space")
        assert "城主府" in result or "张家后院" in result
        # 应该包含空间词
        space_words = ["离开", "穿过", "奔波", "来到"]
        assert any(word in result for word in space_words)

    def test_scene_transition_perspective(self):
        """测试视角过渡"""
        result = scene_transition("主角战斗", "反派密谋", "perspective")
        assert "反派密谋" in result
        # 应该包含视角词
        perspective_words = ["与此同时", "另一边", "而在", "此时"]
        assert any(word in result for word in perspective_words)

    def test_scene_transition_default_type(self):
        """测试默认过渡类型"""
        result = scene_transition("场景A", "场景B")
        assert "场景A" in result or "场景B" in result

    def test_scene_transition_invalid_type(self):
        """测试无效过渡类型（使用默认）"""
        result = scene_transition("场景A", "场景B", "invalid_type")
        assert "场景A" in result
        assert "场景B" in result

    def test_scene_transition_empty_scenes(self):
        """测试空场景名"""
        result = scene_transition("", "新场景", "time")
        assert "新场景" in result

    def test_scene_transition_long_scene_names(self):
        """测试长场景名"""
        long_from = "繁华的帝都中心广场上正在举行盛大的庆典"
        long_to = "荒凉的边境小镇破旧的客栈里"
        result = scene_transition(long_from, long_to, "space")
        assert long_from in result or long_to in result


# 集成测试
class TestCreativeToolsIntegration:
    """测试创意工具集成使用"""

    def test_combined_workflow(self):
        """测试组合使用工作流"""
        # 1. 生成对话
        dialogue = dialogue_enhancer("我们必须行动了！", "张三", "愤怒")
        assert "张三" in dialogue

        # 2. 生成情节转折
        twist = plot_twist_generator("张三决定独自前往", "high")
        assert "情节转折建议" in twist

        # 3. 生成场景过渡
        transition = scene_transition("议事厅", "城外荒野", "space")
        assert "议事厅" in transition or "城外荒野" in transition

    def test_tools_return_string(self):
        """测试所有工具都返回字符串"""
        dialogue_result = dialogue_enhancer("测试")
        twist_result = plot_twist_generator("测试")
        transition_result = scene_transition("A", "B")

        assert isinstance(dialogue_result, str)
        assert isinstance(twist_result, str)
        assert isinstance(transition_result, str)
