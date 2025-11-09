"""测试简化的权限系统"""

from novel_agent.permissions import get_all_tools, get_readonly_tools


def test_readonly_tools() -> None:
    """测试只读模式的工具列表"""
    tools = get_readonly_tools()

    # 验证是列表
    assert isinstance(tools, list)
    assert len(tools) > 0

    # 验证包含只读工具
    assert "read_file" in tools
    assert "search_files" in tools
    assert "check_consistency" in tools
    assert "smart_context_search" in tools
    assert "build_character_network" in tools

    # 验证不包含编辑工具
    assert "write_file" not in tools
    assert "edit_chapter_lines" not in tools
    assert "replace_in_file" not in tools
    assert "multi_edit" not in tools


def test_all_tools() -> None:
    """测试默认模式（所有工具）"""
    result = get_all_tools()  # type: ignore[func-returns-value]

    # None 表示不限制
    assert result is None


def test_readonly_tools_immutable() -> None:
    """测试只读工具列表的不可变性"""
    tools1 = get_readonly_tools()
    tools2 = get_readonly_tools()

    # 每次调用返回新列表
    assert tools1 is not tools2

    # 但内容相同
    assert tools1 == tools2
