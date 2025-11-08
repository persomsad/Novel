"""Novel Agent Tools

实现 5 个核心工具：
1. read_file - 读取任意文件
2. write_chapter - 创建新章节
3. search_content - 搜索关键词
4. verify_strict_timeline - 时间线精确验证
5. verify_strict_references - 引用完整性验证
"""

import subprocess
from pathlib import Path

from .logging_config import get_logger

logger = get_logger(__name__)


def read_file(path: str) -> str:
    """读取文件内容

    Args:
        path: 文件路径（相对或绝对）

    Returns:
        文件内容

    Raises:
        FileNotFoundError: 文件不存在
        PermissionError: 无读取权限
    """
    file_path = Path(path)
    logger.debug(f"正在读取文件: {path}")

    if not file_path.exists():
        logger.error(f"文件不存在: {path}")
        raise FileNotFoundError(f"文件不存在: {path}")

    try:
        content = file_path.read_text(encoding="utf-8")
        logger.info(f"成功读取文件: {path} ({len(content)} 字符)")
        return content
    except PermissionError:
        logger.error(f"无权限读取文件: {path}")
        raise
    except Exception as e:
        logger.error(f"读取文件失败: {path}, 错误: {e}")
        raise


def write_chapter(number: int, content: str, base_dir: str = "chapters") -> str:
    """创建新章节

    Args:
        number: 章节编号（1-999）
        content: 章节内容
        base_dir: 章节目录（默认: chapters）

    Returns:
        创建的文件路径

    Raises:
        ValueError: 章节编号无效
        OSError: 文件系统错误
    """
    logger.debug(f"正在创建章节: 编号={number}, 目录={base_dir}")

    if not 1 <= number <= 999:
        logger.error(f"无效的章节编号: {number}")
        raise ValueError(f"章节编号必须在 1-999 之间，当前: {number}")

    try:
        # 创建目录
        chapters_dir = Path(base_dir)
        chapters_dir.mkdir(parents=True, exist_ok=True)

        # 格式化文件名：ch001.md, ch002.md, ...
        filename = f"ch{number:03d}.md"
        file_path = chapters_dir / filename

        # 写入内容
        file_path.write_text(content, encoding="utf-8")

        logger.info(f"成功创建章节: {file_path} ({len(content)} 字符)")
        return str(file_path)
    except OSError as e:
        logger.error(f"创建章节失败: {e}")
        raise


def search_content(keyword: str, search_dir: str = ".") -> list[dict[str, str]]:
    """搜索关键词

    使用 ripgrep 在指定目录搜索关键词

    Args:
        keyword: 搜索关键词
        search_dir: 搜索目录（默认: 当前目录）

    Returns:
        匹配结果列表，每个结果包含:
        - file: 文件路径
        - line: 行号
        - content: 匹配内容
    """
    logger.debug(f"搜索关键词: '{keyword}' 在目录: {search_dir}")

    try:
        # 使用 rg 搜索
        result = subprocess.run(
            ["rg", "--json", "--fixed-strings", keyword, search_dir],
            capture_output=True,
            text=True,
            check=False,  # 不抛出异常（没有匹配时 rg 返回 1）
        )

        if result.returncode not in (0, 1):
            # 其他错误（2=搜索错误）
            logger.error(f"ripgrep搜索失败: {result.stderr}")
            raise RuntimeError(f"搜索失败: {result.stderr}")

        # 解析 JSON 输出
        import json

        matches: list[dict[str, str]] = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            data = json.loads(line)
            if data.get("type") == "match":
                match_data = data["data"]
                matches.append(
                    {
                        "file": match_data["path"]["text"],
                        "line": str(match_data["line_number"]),
                        "content": match_data["lines"]["text"].strip(),
                    }
                )

        logger.info(f"搜索完成: 找到 {len(matches)} 个匹配")
        return matches

    except FileNotFoundError:
        # ripgrep 未安装，回退到 Python 实现
        logger.warning("ripgrep未安装，使用Python fallback实现")
        return _search_content_fallback(keyword, search_dir)


def _search_content_fallback(keyword: str, search_dir: str) -> list[dict[str, str]]:
    """搜索关键词（Python 实现作为后备）"""
    matches: list[dict[str, str]] = []
    search_path = Path(search_dir)

    # 只搜索 .md 文件
    for file_path in search_path.rglob("*.md"):
        try:
            content = file_path.read_text(encoding="utf-8")
            for line_num, line in enumerate(content.splitlines(), 1):
                if keyword in line:
                    matches.append(
                        {
                            "file": str(file_path),
                            "line": str(line_num),
                            "content": line.strip(),
                        }
                    )
        except Exception:
            # 跳过无法读取的文件
            continue

    return matches


def verify_strict_timeline() -> dict[str, list[str]]:
    """时间线精确验证

    调用外部脚本检查时间线数字一致性

    Returns:
        验证结果：
        - errors: 错误列表
        - warnings: 警告列表
    """
    # TODO: 实现时间线检查脚本
    # 目前返回空结果
    return {"errors": [], "warnings": []}


def verify_strict_references() -> dict[str, list[str]]:
    """引用完整性验证

    调用外部脚本检查引用 ID 完整性

    Returns:
        验证结果：
        - errors: 错误列表（引用不存在）
        - warnings: 警告列表（未使用的伏笔）
    """
    # TODO: 实现引用检查脚本
    # 目前返回空结果
    return {"errors": [], "warnings": []}
