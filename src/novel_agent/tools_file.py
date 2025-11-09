"""通用文件操作工具

支持创建任意路径的文件和目录，参考 ultrathink 和 MCP File Server 设计。
"""

from pathlib import Path

from langchain_core.tools import tool

from .logging_config import get_logger

logger = get_logger(__name__)

# 禁止操作的关键目录和文件
FORBIDDEN_PATHS = {
    ".git",
    "src",
    "tests",
    "pyproject.toml",
    "poetry.lock",
    ".env",
    ".venv",
    "node_modules",
    "__pycache__",
}


def _validate_path(path: str) -> Path:
    """验证路径安全性

    Args:
        path: 文件或目录路径

    Returns:
        验证后的 Path 对象

    Raises:
        ValueError: 路径不安全
    """
    # 检查1：禁止包含 ..（路径遍历）
    if ".." in path:
        raise ValueError(f"禁止使用相对路径 '..': {path}")

    # 转换为 Path 对象
    target_path = Path(path).resolve()
    current_dir = Path.cwd().resolve()

    # 检查2：禁止访问项目外部
    try:
        target_path.relative_to(current_dir)
    except ValueError:
        raise ValueError(f"禁止访问项目外部路径: {path}")

    # 检查3：禁止操作关键目录/文件
    for forbidden in FORBIDDEN_PATHS:
        forbidden_path = current_dir / forbidden
        # 检查是否在禁止目录内或就是禁止目录本身
        if target_path == forbidden_path:
            raise ValueError(f"禁止操作关键文件/目录: {forbidden}")
        try:
            target_path.relative_to(forbidden_path)
            raise ValueError(f"禁止操作关键目录: {forbidden}")
        except ValueError as e:
            # 不在禁止目录内，继续检查下一个
            if "禁止操作关键目录" in str(e):
                raise
            continue

    return target_path


@tool
def create_file(path: str, content: str) -> str:
    """创建文件（支持任意路径）

    自动创建所需的父目录。如果文件已存在会覆盖。

    Args:
        path: 文件路径（相对于项目根目录）
        content: 文件内容

    Returns:
        创建的文件路径

    Examples:
        >>> create_file("chapters/ch001.md", "# 第一章\\n...")
        'chapters/ch001.md'

        >>> create_file("spec/characters/张三.md", "## 角色：张三\\n...")
        'spec/characters/张三.md'

        >>> create_file("chapters/卷一/ch001.md", "# 第一章\\n...")
        'chapters/卷一/ch001.md'

    Raises:
        ValueError: 路径不安全
        OSError: 文件系统错误
    """
    logger.debug(f"正在创建文件: {path}")

    try:
        # 验证路径安全性
        file_path = _validate_path(path)

        # 创建父目录
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入内容
        file_path.write_text(content, encoding="utf-8")

        logger.info(f"成功创建文件: {path} ({len(content)} 字符)")
        return str(path)
    except ValueError as e:
        logger.error(f"路径验证失败: {e}")
        raise
    except OSError as e:
        logger.error(f"创建文件失败: {e}")
        raise


@tool
def create_directory(path: str) -> str:
    """创建目录（支持多级目录）

    Args:
        path: 目录路径（相对于项目根目录）

    Returns:
        创建的目录路径

    Examples:
        >>> create_directory("chapters/卷一")
        'chapters/卷一'

        >>> create_directory("spec/characters")
        'spec/characters'

        >>> create_directory("chapters/卷一/第一部分")
        'chapters/卷一/第一部分'

    Raises:
        ValueError: 路径不安全
        OSError: 文件系统错误
    """
    logger.debug(f"正在创建目录: {path}")

    try:
        # 验证路径安全性
        dir_path = _validate_path(path)

        # 创建目录
        dir_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"成功创建目录: {path}")
        return str(path)
    except ValueError as e:
        logger.error(f"路径验证失败: {e}")
        raise
    except OSError as e:
        logger.error(f"创建目录失败: {e}")
        raise


@tool
def list_files(path: str = ".") -> str:
    """列出目录内容

    Args:
        path: 目录路径（默认当前目录）

    Returns:
        目录内容列表（格式化字符串）

    Examples:
        >>> list_files("chapters")
        📁 chapters (3 项)
        📄 ch001.md (1234 字节)
        📄 ch002.md (2345 字节)
        📁 卷一/

        >>> list_files()
        📁 . (5 项)
        📁 chapters/
        📁 spec/
        📄 README.md (12345 字节)

    Raises:
        ValueError: 路径不安全
        OSError: 目录不存在或无权限
    """
    logger.debug(f"正在列出目录: {path}")

    try:
        # 验证路径安全性
        dir_path = _validate_path(path)

        # 检查目录是否存在
        if not dir_path.exists():
            raise FileNotFoundError(f"目录不存在: {path}")

        if not dir_path.is_dir():
            raise ValueError(f"不是目录: {path}")

        # 列出内容
        items = sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name))

        if not items:
            return f"📁 {path} (空目录)"

        lines = [f"📁 {path} ({len(items)} 项)"]
        for item in items:
            if item.is_dir():
                lines.append(f"📁 {item.name}/")
            else:
                size = item.stat().st_size
                lines.append(f"📄 {item.name} ({size} 字节)")

        result = "\n".join(lines)
        logger.info(f"成功列出目录: {path} ({len(items)} 项)")
        return result
    except ValueError as e:
        logger.error(f"路径验证失败: {e}")
        raise
    except OSError as e:
        logger.error(f"列出目录失败: {e}")
        raise
