"""Prompt 文件加载器

支持从 Markdown 文件加载 Prompt，带变量替换和 YAML frontmatter 解析
"""

from pathlib import Path
from typing import cast

import frontmatter  # type: ignore[import-untyped]


def load_prompt_from_file(file_path: str, variables: dict[str, str] | None = None) -> str:
    """从文件加载 Prompt

    Args:
        file_path: Prompt 文件路径
        variables: 变量替换字典

    Returns:
        处理后的 prompt 内容

    Raises:
        FileNotFoundError: 文件不存在
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {file_path}")

    # 使用 python-frontmatter 解析
    post = frontmatter.load(path)

    # 获取内容（cast 为 str 以满足 mypy）
    content = cast(str, post.content)

    # 变量替换
    if variables:
        for key, value in variables.items():
            content = content.replace(f"${{{key}}}", value)

    return content


def parse_variables(var_list: list[str]) -> dict[str, str]:
    """解析变量列表

    Args:
        var_list: ["KEY1=value1", "KEY2=value2"]

    Returns:
        {"KEY1": "value1", "KEY2": "value2"}
    """
    variables = {}
    for var in var_list:
        if "=" in var:
            key, value = var.split("=", 1)
            variables[key.strip()] = value.strip()
    return variables
