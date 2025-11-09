"""测试 Prompt 文件加载器"""

from pathlib import Path

import pytest

from novel_agent.prompt_loader import load_prompt_from_file, parse_variables


def test_load_basic_prompt(tmp_path: Path) -> None:
    """测试基础文件读取"""
    prompt_file = tmp_path / "test.md"
    prompt_file.write_text("检查一致性", encoding="utf-8")

    content = load_prompt_from_file(str(prompt_file))
    assert content == "检查一致性"


def test_load_prompt_file_not_found() -> None:
    """测试文件不存在"""
    with pytest.raises(FileNotFoundError, match="Prompt 文件不存在"):
        load_prompt_from_file("nonexistent.md")


def test_variable_replacement(tmp_path: Path) -> None:
    """测试变量替换"""
    prompt_file = tmp_path / "test.md"
    prompt_file.write_text("检查 ${CHAPTER} 的一致性", encoding="utf-8")

    content = load_prompt_from_file(str(prompt_file), variables={"CHAPTER": "ch001.md"})
    assert content == "检查 ch001.md 的一致性"


def test_multiple_variables(tmp_path: Path) -> None:
    """测试多个变量替换"""
    prompt_file = tmp_path / "test.md"
    prompt_file.write_text("检查 ${CHAPTER} 的 ${FOCUS} 方面", encoding="utf-8")

    content = load_prompt_from_file(
        str(prompt_file), variables={"CHAPTER": "ch001.md", "FOCUS": "角色一致性"}
    )
    assert content == "检查 ch001.md 的 角色一致性 方面"


def test_frontmatter_parsing(tmp_path: Path) -> None:
    """测试 YAML frontmatter"""
    prompt_file = tmp_path / "test.md"
    prompt_file.write_text("---\ndescription: 测试\nauthor: 团队\n---\n内容", encoding="utf-8")

    content = load_prompt_from_file(str(prompt_file))
    assert content.strip() == "内容"


def test_frontmatter_with_variables(tmp_path: Path) -> None:
    """测试 frontmatter + 变量替换"""
    prompt_file = tmp_path / "test.md"
    prompt_file.write_text(
        "---\ndescription: 检查章节\n---\n检查 ${CHAPTER}",
        encoding="utf-8",
    )

    content = load_prompt_from_file(str(prompt_file), variables={"CHAPTER": "ch001"})
    assert "检查 ch001" in content


def test_parse_variables() -> None:
    """测试变量列表解析"""
    var_list = ["KEY1=value1", "KEY2=value2", "KEY3=value with spaces"]

    variables = parse_variables(var_list)

    assert variables == {
        "KEY1": "value1",
        "KEY2": "value2",
        "KEY3": "value with spaces",
    }


def test_parse_variables_empty_list() -> None:
    """测试空变量列表"""
    variables = parse_variables([])
    assert variables == {}


def test_parse_variables_no_equals() -> None:
    """测试无效格式（无等号）"""
    var_list = ["KEY1=value1", "INVALID", "KEY2=value2"]

    variables = parse_variables(var_list)

    # 只解析有效的
    assert variables == {"KEY1": "value1", "KEY2": "value2"}


def test_multiline_prompt(tmp_path: Path) -> None:
    """测试多行 prompt"""
    prompt_file = tmp_path / "test.md"
    prompt_file.write_text(
        "请检查章节的以下方面：\n" "1. 角色一致性\n" "2. 情节逻辑\n" "3. 时间线",
        encoding="utf-8",
    )

    content = load_prompt_from_file(str(prompt_file))
    assert "角色一致性" in content
    assert "情节逻辑" in content
    assert "时间线" in content


def test_chinese_content(tmp_path: Path) -> None:
    """测试中文内容"""
    prompt_file = tmp_path / "test.md"
    prompt_file.write_text("检查第一章的角色一致性问题", encoding="utf-8")

    content = load_prompt_from_file(str(prompt_file))
    assert content == "检查第一章的角色一致性问题"
