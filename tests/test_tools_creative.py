from novel_agent import tools_creative as tc


def test_calculate_word_count() -> None:
    stats = tc.calculate_word_count("你好 世界。再见！")
    assert stats["words"] >= 2
    assert stats["sentences"] == 2


def test_random_name_generator_deterministic() -> None:
    name1 = tc.random_name_generator("xuanhuan", "male", seed=42)
    name2 = tc.random_name_generator("xuanhuan", "male", seed=42)
    assert name1 == name2


def test_style_analyzer_detects_tone() -> None:
    report = tc.style_analyzer("他狂笑着冲向战场！这是他的胜利！")
    assert report["tone"] in {"激昂", "平稳", "细腻", "轻快"}


def test_dialogue_enhancer_adds_beats() -> None:
    output = tc.dialogue_enhancer("你是谁？", character_hint="李明")
    assert "李明" in output


def test_plot_twist_generator_returns_list() -> None:
    """测试情节转折生成器返回格式化字符串"""
    result = tc.plot_twist_generator("李明与张强合作", intensity="high", seed=1)
    # 应该返回字符串而不是列表
    assert isinstance(result, str)
    assert "情节转折建议" in result
    assert "高强度" in result
    # 应该有多个建议（检查编号）
    assert "1." in result
    assert "2." in result
