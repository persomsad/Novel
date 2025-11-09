"""工具权限管理

简化的 2 级权限系统：
- 默认模式：所有工具（None = 不限制）
- 只读模式：仅读取和分析工具
"""


def get_readonly_tools() -> list[str]:
    """获取只读模式允许的工具列表

    只读模式适用于：
    - 审稿和分析
    - 学习小说结构
    - 检查一致性
    - 不需要修改文件的场景

    Returns:
        允许的工具名称列表
    """
    return [
        # 基础文件操作（只读）
        "read_file",
        "read_multiple_files",
        "search_files",
        # 一致性检查
        "check_consistency",
        "verify_strict_timeline",
        "verify_strict_references",
        # 图查询和分析
        "smart_context_search",
        "build_character_network",
        "trace_foreshadow",
    ]


def get_all_tools() -> None:
    """获取所有工具（None = 不限制）

    默认模式适用于：
    - 小说创作
    - 章节编辑
    - 批量修改
    - 正常写作场景

    Returns:
        None（表示允许所有工具）
    """
    return None
