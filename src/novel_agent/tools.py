"""Novel Agent Tools

实现 5 个核心工具：
1. read_file - 读取任意文件
2. write_chapter - 创建新章节
3. search_content - 搜索关键词
4. verify_strict_timeline - 时间线精确验证
5. verify_strict_references - 引用完整性验证
"""

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import frontmatter  # type: ignore
from langchain_core.tools import tool as lc_tool

from . import nervus_cli
from .logging_config import get_logger
from .tools_creative import dialogue_enhancer, plot_twist_generator, scene_transition

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


def _load_continuity_index(path: Path | None = None) -> dict[str, Any]:
    target = path or Path("data/continuity/index.json")
    if not target.exists():
        raise FileNotFoundError(
            f"连续性索引 {target} 不存在。请先运行 `poetry run novel-agent refresh-memory`。"
        )
    result: dict[str, Any] = json.loads(target.read_text(encoding="utf-8"))
    return result


def _get_nervus_db_path(explicit: str | None = None) -> str | None:
    return explicit or os.getenv("NERVUSDB_DB_PATH")


def _fetch_nervus_events(db_path: str) -> list[tuple[str, str]]:
    try:
        result = nervus_cli.cypher_query(
            db_path,
            """
            MATCH (ch:Chapter)-[:HAS_EVENT]->(e:Event)
            RETURN ch.id as chapter_id, e.timestamp as timestamp
            ORDER BY chapter_id, timestamp
            """,
        )
    except Exception as exc:
        raise RuntimeError(f"NervusDB 时间线查询失败: {exc}") from exc

    rows = result.get("rows") if isinstance(result, dict) else result
    if not rows and isinstance(result, dict) and "result" in result:
        rows = result["result"]
    events: list[tuple[str, str]] = []
    for row in rows or []:
        chapter_id = row.get("chapter_id") or row.get("CHAPTER_ID")
        timestamp = row.get("timestamp") or row.get("TIMESTAMP")
        if chapter_id and timestamp:
            events.append((str(chapter_id), str(timestamp)))
    return events


def _fetch_nervus_references(db_path: str) -> set[tuple[str, str]]:
    try:
        result = nervus_cli.cypher_query(
            db_path,
            """
            MATCH (ch:Chapter)-[:USES_REFERENCE]->(r:Reference)
            RETURN ch.id as chapter_id, r.id as ref_id
            """,
        )
    except Exception as exc:
        raise RuntimeError(f"NervusDB 引用查询失败: {exc}") from exc

    rows = result.get("rows") if isinstance(result, dict) else result
    if not rows and isinstance(result, dict) and "result" in result:
        rows = result["result"]
    refs: set[tuple[str, str]] = set()
    for row in rows or []:
        chapter_id = row.get("chapter_id") or row.get("CHAPTER_ID")
        ref_id = row.get("ref_id") or row.get("REF_ID")
        if chapter_id and ref_id:
            refs.add((str(chapter_id), str(ref_id)))
    return refs


def verify_strict_timeline(
    index_path: Path | None = None,
    *,
    db_path: str | None = None,
) -> dict[str, Any]:
    """时间线精确验证（增强版：输出行号和修复建议）

    Returns:
        {
            "errors": [
                {
                    "file": "chapters/ch002.md",
                    "line": 42,
                    "type": "timeline_inconsistency",
                    "message": "时间倒退：前一章是 2077-03-15，此处是 2077-03-10",
                    "suggestion": "将 [TIME:2077-03-10] 改为 [TIME:2077-03-16] 或更晚",
                    "current_value": "2077-03-10",
                    "expected_value": "2077-03-16"
                }
            ],
            "warnings": [...],
            "summary": {
                "total_errors": 2,
                "total_warnings": 1,
                "auto_fixable": True
            }
        }
    """

    data = _load_continuity_index(index_path)
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    def parse_date(value: str) -> datetime | None:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

    last_date: datetime | None = None
    last_chapter_id: str = ""

    for chapter in sorted(data.get("chapters", []), key=lambda c: c.get("chapter_id", "")):
        chapter_id = chapter.get("chapter_id")
        for marker in chapter.get("time_markers", []):
            value = marker.get("value")
            line_number = marker.get("line", 0)
            dt = parse_date(value)

            if not dt:
                warnings.append(
                    {
                        "file": f"chapters/{chapter_id}.md",
                        "line": line_number,
                        "type": "unparseable_time",
                        "message": f"时间标记 `{value}` 无法解析",
                        "suggestion": "请使用 YYYY-MM-DD、YYYY/MM/DD 或 YYYY.MM.DD 格式",
                        "current_value": value,
                    }
                )
                continue

            if last_date and dt < last_date:
                # 计算建议的日期（前一个日期 + 1天）
                from datetime import timedelta

                suggested_date = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")

                prev_date = last_date.date()
                curr_date = dt.date()
                errors.append(
                    {
                        "file": f"chapters/{chapter_id}.md",
                        "line": line_number,
                        "type": "timeline_inconsistency",
                        "message": (
                            f"时间倒退：前一章节 ({last_chapter_id}) "
                            f"是 {prev_date}，此处是 {curr_date}"
                        ),
                        "suggestion": f"将 [TIME:{value}] 改为 [TIME:{suggested_date}] 或更晚",
                        "current_value": value,
                        "expected_value": suggested_date,
                        "previous_chapter": last_chapter_id,
                        "previous_date": str(prev_date),
                    }
                )

            last_date = dt
            last_chapter_id = chapter_id

    # NervusDB 比对
    nervus_db = _get_nervus_db_path(db_path)
    if nervus_db:
        try:
            db_events = _fetch_nervus_events(nervus_db)
            db_set = set(db_events)
            local_set = {
                (chapter.get("chapter_id"), marker.get("value"))
                for chapter in data.get("chapters", [])
                for marker in chapter.get("time_markers", [])
            }

            for chapter in data.get("chapters", []):
                cid = chapter.get("chapter_id")
                for marker in chapter.get("time_markers", []):
                    value = marker.get("value")
                    line_number = marker.get("line", 0)
                    if (cid, value) not in db_set:
                        errors.append(
                            {
                                "file": f"chapters/{cid}.md",
                                "line": line_number,
                                "type": "missing_in_nervus",
                                "message": f"时间标记 `{value}` 未写入 NervusDB",
                                "suggestion": "运行 'novel-agent memory ingest' 同步到 NervusDB",
                                "current_value": value,
                            }
                        )

            extra = db_set - local_set
            for cid, value in sorted(extra):
                warnings.append(
                    {
                        "file": f"chapters/{cid}.md",
                        "line": 0,
                        "type": "extra_in_nervus",
                        "message": f"NervusDB 中存在未在章节出现的时间 `{value}`",
                        "suggestion": f"检查章节 {cid} 是否删除了此时间标记",
                        "current_value": value,
                    }
                )
        except RuntimeError as exc:
            warnings.append(
                {
                    "file": "NervusDB",
                    "line": 0,
                    "type": "nervus_error",
                    "message": str(exc),
                    "suggestion": "检查 NervusDB 配置和数据库连接",
                }
            )

    # 计算自动修复能力
    auto_fixable = all(err.get("expected_value") for err in errors)

    return {
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total_errors": len(errors),
            "total_warnings": len(warnings),
            "auto_fixable": auto_fixable,
        },
    }


def verify_strict_references(
    index_path: Path | None = None,
    *,
    db_path: str | None = None,
) -> dict[str, Any]:
    """引用完整性验证（增强版：输出行号和修复建议）

    Returns:
        {
            "errors": [
                {
                    "file": "chapters/ch003.md",
                    "line": 56,
                    "type": "undefined_reference",
                    "message": "引用 `sword_of_destiny` 未定义",
                    "suggestion": "在 spec/knowledge/ 中添加此引用的定义，或检查拼写错误",
                    "current_value": "sword_of_destiny"
                }
            ],
            "warnings": [...],
            "summary": {
                "total_errors": 1,
                "total_warnings": 2,
                "auto_fixable": False
            }
        }
    """

    data = _load_continuity_index(index_path)
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    reference_map = {ref["id"]: ref["occurrences"] for ref in data.get("references", [])}

    # 检查未使用的引用定义
    for ref_id, occurrences in reference_map.items():
        if not occurrences:
            warnings.append(
                {
                    "file": "spec/knowledge/",
                    "line": 0,
                    "type": "unused_reference",
                    "message": f"引用 `{ref_id}` 无任何章节使用",
                    "suggestion": f"考虑删除此引用定义，或在章节中添加 [REF:{ref_id}]",
                    "current_value": ref_id,
                }
            )

    # 检查未定义的引用
    defined = set(reference_map.keys())
    for chapter in data.get("chapters", []):
        chapter_id = chapter.get("chapter_id")
        for ref in chapter.get("references", []):
            ref_id = ref.get("id")
            line_number = ref.get("line", 0)

            if ref_id not in defined:
                errors.append(
                    {
                        "file": f"chapters/{chapter_id}.md",
                        "line": line_number,
                        "type": "undefined_reference",
                        "message": f"引用 `{ref_id}` 未定义",
                        "suggestion": "在 spec/knowledge/ 中添加此引用的定义，或检查拼写错误",
                        "current_value": ref_id,
                    }
                )

    # NervusDB 比对
    nervus_db = _get_nervus_db_path(db_path)
    if nervus_db:
        try:
            db_refs = _fetch_nervus_references(nervus_db)
            db_set = set(db_refs)
            local_refs = {
                (chapter.get("chapter_id"), ref.get("id"))
                for chapter in data.get("chapters", [])
                for ref in chapter.get("references", [])
            }

            for chapter in data.get("chapters", []):
                cid = chapter.get("chapter_id")
                for ref in chapter.get("references", []):
                    ref_id = ref.get("id")
                    line_number = ref.get("line", 0)

                    if (cid, ref_id) not in db_set:
                        errors.append(
                            {
                                "file": f"chapters/{cid}.md",
                                "line": line_number,
                                "type": "missing_in_nervus",
                                "message": f"引用 `{ref_id}` 未写入 NervusDB",
                                "suggestion": "运行 'novel-agent memory ingest' 同步到 NervusDB",
                                "current_value": ref_id,
                            }
                        )

            extra_refs = db_set - local_refs
            for cid, ref_id in sorted(extra_refs):
                warnings.append(
                    {
                        "file": f"chapters/{cid}.md",
                        "line": 0,
                        "type": "extra_in_nervus",
                        "message": f"NervusDB 中存在未在章节使用的引用 `{ref_id}`",
                        "suggestion": f"检查章节 {cid} 是否删除了此引用",
                        "current_value": ref_id,
                    }
                )
        except RuntimeError as exc:
            warnings.append(
                {
                    "file": "NervusDB",
                    "line": 0,
                    "type": "nervus_error",
                    "message": str(exc),
                    "suggestion": "检查 NervusDB 配置和数据库连接",
                }
            )

    # 引用验证通常不能自动修复（需要手动定义或删除）
    auto_fixable = False

    return {
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total_errors": len(errors),
            "total_warnings": len(warnings),
            "auto_fixable": auto_fixable,
        },
    }


def edit_chapter_lines(
    chapter_number: int,
    start_line: int,
    end_line: int,
    new_content: str,
    base_dir: str = "chapters",
) -> str:
    """精准修改章节的指定行

    Args:
        chapter_number: 章节编号
        start_line: 起始行号（从1开始）
        end_line: 结束行号（包含，从1开始）
        new_content: 新内容（替换指定行）
        base_dir: 章节目录

    Returns:
        操作结果描述

    Raises:
        FileNotFoundError: 章节文件不存在
        ValueError: 行号参数无效

    Example:
        >>> # 修改第10-12行
        >>> edit_chapter_lines(1, 10, 12, "新的内容\\n替换这三行")
    """
    if chapter_number < 1:
        raise ValueError(f"章节编号必须 >= 1，当前: {chapter_number}")

    if start_line < 1 or end_line < start_line:
        raise ValueError(f"行号无效: start={start_line}, end={end_line}")

    chapter_path = Path(base_dir) / f"ch{chapter_number:03d}.md"

    if not chapter_path.exists():
        raise FileNotFoundError(f"章节不存在: {chapter_path}")

    logger.info(f"正在修改章节 {chapter_number} 的第 {start_line}-{end_line} 行: {chapter_path}")

    # 读取原文件
    lines = chapter_path.read_text(encoding="utf-8").splitlines(keepends=True)
    total_lines = len(lines)

    if end_line > total_lines:
        raise ValueError(f"结束行号 {end_line} 超出文件总行数 {total_lines}")

    # 替换指定行（注意：行号从1开始，数组索引从0开始）
    new_lines = new_content.splitlines(keepends=True)

    # 确保新内容以换行符结尾
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"

    # 组合：前半部分 + 新内容 + 后半部分
    result_lines = lines[: start_line - 1] + new_lines + lines[end_line:]

    # 写回文件
    chapter_path.write_text("".join(result_lines), encoding="utf-8")

    logger.info(f"✅ 成功修改章节 {chapter_number} (第 {start_line}-{end_line} 行)")
    return (
        f"✅ 成功修改章节 {chapter_number} "
        f"(第 {start_line}-{end_line} 行，共 {len(new_lines)} 行新内容)"
    )


def replace_in_file(
    file_path: str,
    search_text: str,
    replacement: str,
    occurrence: int | None = None,
) -> str:
    """在文件中查找并替换文本

    Args:
        file_path: 文件路径
        search_text: 要查找的文本
        replacement: 替换文本
        occurrence: 替换第几次出现（None=全部替换，1=第一次，2=第二次...）

    Returns:
        操作结果描述

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: search_text 不存在

    Example:
        >>> # 替换所有"张三"为"李四"
        >>> replace_in_file("chapters/ch001.md", "张三", "李四")

        >>> # 只替换第一次出现的"张三"
        >>> replace_in_file("chapters/ch001.md", "张三", "李四", occurrence=1)
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    logger.info(f"正在查找替换: {file_path} ('{search_text}' → '{replacement}')")

    content = path.read_text(encoding="utf-8")

    if search_text not in content:
        raise ValueError(f"未找到要替换的文本: '{search_text}'")

    # 计算出现次数
    count = content.count(search_text)

    if occurrence is not None:
        if occurrence < 1 or occurrence > count:
            raise ValueError(f"occurrence 参数无效: {occurrence} (文本共出现 {count} 次)")

        # 替换指定的第 N 次出现
        parts = content.split(search_text)
        new_content = (
            search_text.join(parts[:occurrence])
            + replacement
            + search_text.join(parts[occurrence:])
        )
        replaced_count = 1
    else:
        # 替换所有出现
        new_content = content.replace(search_text, replacement)
        replaced_count = count

    path.write_text(new_content, encoding="utf-8")

    logger.info(f"✅ 成功替换 {replaced_count} 处文本: {file_path}")
    return f"✅ 成功替换 {replaced_count} 处文本: {file_path} (共出现 {count} 次)"


def multi_edit(operations: list[dict[str, Any]]) -> str:
    """批量编辑多个文件

    Args:
        operations: 编辑操作列表，每个操作包含：
            - type: "replace" | "edit_lines"
            - file: 文件路径
            - ... 其他参数取决于 type

    Returns:
        操作结果描述

    Raises:
        ValueError: 操作参数无效
        RuntimeError: 编辑失败（会回滚所有操作）

    Example:
        >>> operations = [
        ...     {
        ...         "type": "replace",
        ...         "file": "chapters/ch001.md",
        ...         "search": "张三",
        ...         "replace": "李四"
        ...     },
        ...     {
        ...         "type": "replace",
        ...         "file": "chapters/ch002.md",
        ...         "search": "张三",
        ...         "replace": "李四"
        ...     },
        ... ]
        >>> multi_edit(operations)
    """
    if not operations:
        return "⚠️ 没有操作需要执行"

    logger.info(f"开始批量编辑：{len(operations)} 个操作")

    # 备份所有文件
    backups: dict[str, str] = {}
    modified_files: list[str] = []

    try:
        # 第一步：备份所有文件
        for op in operations:
            file_path = op.get("file")
            if not file_path:
                raise ValueError(f"操作缺少 'file' 参数: {op}")

            path = Path(file_path)
            if path.exists() and file_path not in backups:
                backups[file_path] = path.read_text(encoding="utf-8")

        # 第二步：执行所有操作
        for i, op in enumerate(operations, 1):
            op_type = op.get("type")
            file_path = op["file"]

            logger.debug(f"执行操作 {i}/{len(operations)}: {op_type} on {file_path}")

            if op_type == "replace":
                replace_in_file(
                    file_path,
                    op["search"],
                    op["replace"],
                    op.get("occurrence"),
                )
                modified_files.append(file_path)

            elif op_type == "edit_lines":
                # 提取章节编号
                chapter_number = op.get("chapter_number")
                if chapter_number is None:
                    # 尝试从文件名提取
                    match = Path(file_path).stem
                    if match.startswith("ch") and match[2:5].isdigit():
                        chapter_number = int(match[2:5])
                    else:
                        raise ValueError(f"无法确定章节编号: {file_path}")

                edit_chapter_lines(
                    chapter_number,
                    op["start_line"],
                    op["end_line"],
                    op["new_content"],
                    base_dir=str(Path(file_path).parent),
                )
                modified_files.append(file_path)

            else:
                raise ValueError(f"不支持的操作类型: {op_type}")

        logger.info(f"✅ 批量编辑完成：修改了 {len(set(modified_files))} 个文件")
        return (
            f"✅ 批量编辑完成：修改了 {len(set(modified_files))} 个文件 ({len(operations)} 个操作)"
        )

    except Exception as e:
        # 回滚所有修改
        logger.error(f"批量编辑失败，正在回滚: {e}")

        for file_path, backup_content in backups.items():
            try:
                Path(file_path).write_text(backup_content, encoding="utf-8")
                logger.debug(f"已回滚: {file_path}")
            except Exception as rollback_err:
                logger.error(f"回滚失败: {file_path} - {rollback_err}")

        raise RuntimeError(f"批量编辑失败，已回滚所有修改: {e}") from e


# ========== 图查询工具 (Graph Query Tools) ==========


def smart_context_search_tool(
    query: str,
    search_type: str = "all",
    max_hops: int = 2,
    limit: int = 10,
) -> str:
    """智能上下文搜索（基于图数据库）

    使用 NervusDB 图数据库进行智能上下文检索，比向量检索更精准、更可解释。

    Args:
        query: 搜索查询（如"张三和李四的关系"）
        search_type: 'character' | 'location' | 'event' | 'foreshadow' | 'all'
        max_hops: 最大关系跳数（1-3，默认 2）
        limit: 最多返回结果数（默认 10）

    Returns:
        格式化的搜索结果，包含：
        - 直接匹配的实体
        - 通过关系关联的实体
        - 图路径和置信度
        - 统计信息

    Example:
        >>> smart_context_search_tool("张三", "character", max_hops=2, limit=5)
        找到 5 个相关结果：
          - character: 2 个
          - chapter: 3 个

        1. [直接匹配] 张三 (character)
           置信度: 1.0

        2. [1 跳关系] 李四 (character)
           路径: 张三 -> 李四
           置信度: 0.5

        ...
    """
    from .graph_query import smart_context_search

    logger.info(f"图查询: {query}, 类型={search_type}, 跳数={max_hops}")

    try:
        db_path = os.getenv("NOVEL_GRAPH_DB", "data/novel-graph.nervusdb")
        result = smart_context_search(
            query=query,
            db_path=db_path,
            search_type=search_type,  # type: ignore
            max_hops=max_hops,
            limit=limit,
        )

        # 格式化输出
        output = [result["summary"], ""]

        for i, item in enumerate(result["results"], 1):
            output.append(f"{i}. [{item['relevance']}] {item['name']} ({item['type']})")
            if item["path"] and len(item["path"]) > 1:
                output.append(f"   路径: {' -> '.join(item['path'])}")
            output.append(f"   置信度: {item['confidence']:.2f}")
            output.append("")

        # 添加统计
        stats = result["graph_stats"]
        output.append(
            f"📊 统计: 搜索了 {stats['nodes_searched']} 个节点，最大深度 {stats['max_depth']}"
        )

        return "\n".join(output)

    except Exception as e:
        logger.error(f"图查询失败: {e}")
        return f"❌ 图查询失败: {e}\n提示：请先运行 'novel-agent build-graph' 构建图数据库"


def build_character_network_tool(character_names: str | None = None) -> str:
    """构建角色关系网络图

    分析角色之间的关系，构建社交网络图。

    Args:
        character_names: 角色名列表（逗号分隔，如"张三,李四,王五"）
                        留空则分析所有角色

    Returns:
        格式化的网络信息：
        - 节点（角色）列表
        - 边（关系）列表
        - 社区（群组）检测结果

    Example:
        >>> build_character_network_tool("张三,李四")
        角色网络分析结果：

        节点 (2 个):
        1. 张三 (protagonist)
        2. 李四 (supporting)

        关系 (1 条):
        1. 张三 -[knows]-> 李四 (强度: 0.9)

        社区 (1 个):
        - 社区 1: 张三, 李四 (2 人)
    """
    from .graph_query import build_character_network

    logger.info(f"构建角色网络: {character_names or '所有角色'}")

    try:
        db_path = os.getenv("NOVEL_GRAPH_DB", "data/novel-graph.nervusdb")
        names_list = (
            [n.strip() for n in character_names.split(",") if n.strip()]
            if character_names
            else None
        )

        result = build_character_network(db_path=db_path, character_names=names_list)

        # 格式化输出
        output = ["角色网络分析结果：", ""]

        # 节点
        output.append(f"节点 ({len(result['nodes'])} 个):")
        for i, node in enumerate(result["nodes"][:20], 1):  # 限制显示前 20 个
            node_type = node.get("properties", {}).get("type", node["type"])
            output.append(f"{i}. {node['label']} ({node_type})")
        if len(result["nodes"]) > 20:
            output.append(f"... 还有 {len(result['nodes']) - 20} 个节点")
        output.append("")

        # 关系
        output.append(f"关系 ({len(result['edges'])} 条):")
        for i, edge in enumerate(result["edges"][:20], 1):
            weight = edge.get("weight", 1.0)
            relation = f"{edge['source']} -[{edge['relation']}]-> {edge['target']}"
            output.append(f"{i}. {relation} (强度: {weight:.2f})")
        if len(result["edges"]) > 20:
            output.append(f"... 还有 {len(result['edges']) - 20} 条关系")
        output.append("")

        # 社区
        output.append(f"社区 ({len(result['clusters'])} 个):")
        for cluster in result["clusters"][:10]:
            members_str = ", ".join(cluster["members"][:5])
            if len(cluster["members"]) > 5:
                members_str += f" ... 共 {cluster['size']} 人"
            output.append(f"- {cluster['label']}: {members_str}")
        if len(result["clusters"]) > 10:
            output.append(f"... 还有 {len(result['clusters']) - 10} 个社区")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"构建角色网络失败: {e}")
        return f"❌ 构建角色网络失败: {e}\n提示：请先运行 'novel-agent build-graph' 构建图数据库"


def trace_foreshadow_tool(foreshadow_id: str) -> str:
    """追溯伏笔完整链条

    追踪伏笔从埋下到揭晓的完整过程。

    Args:
        foreshadow_id: 伏笔 ID（如 "foreshadow_001"）

    Returns:
        格式化的伏笔追溯结果：
        - Setup（埋笔）章节
        - Hints（暗示）列表
        - Reveal（揭晓）章节
        - 状态（已解决/未解决）

    Example:
        >>> trace_foreshadow_tool("foreshadow_001")
        伏笔追溯: foreshadow_001

        📍 埋笔 (Setup):
        - 第 5 章

        💡 暗示 (Hints):
        - 第 5 章: 首次提及
        - 第 8 章: 隐晦暗示
        - 第 12 章: 明确暗示

        🎯 揭晓 (Reveal):
        - 第 20 章

        ✅ 状态: 已解决
    """
    from .graph_query import trace_foreshadow

    logger.info(f"追溯伏笔: {foreshadow_id}")

    try:
        db_path = os.getenv("NOVEL_GRAPH_DB", "data/novel-graph.nervusdb")
        result = trace_foreshadow(foreshadow_id=foreshadow_id, db_path=db_path)

        if "error" in result:
            return f"❌ {result['error']}"

        # 格式化输出
        output = [f"伏笔追溯: {foreshadow_id}", ""]

        # Setup
        if result.get("setup"):
            setup = result["setup"]
            output.append("📍 埋笔 (Setup):")
            output.append(f"- 第 {setup['chapter']} 章")
            output.append("")

        # Hints
        hints = result.get("hints", [])
        if hints:
            output.append(f"💡 暗示 (Hints, {len(hints)} 处):")
            for hint in hints:
                output.append(f"- 第 {hint['chapter']} 章")
            output.append("")

        # Reveal
        if result.get("reveal"):
            reveal = result["reveal"]
            output.append("🎯 揭晓 (Reveal):")
            output.append(f"- 第 {reveal['chapter']} 章")
            output.append("")

        # Status
        status_emoji = "✅" if result["status"] == "resolved" else "⚠️ "
        status_text = "已解决" if result["status"] == "resolved" else "未解决"
        output.append(f"{status_emoji} 状态: {status_text}")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"追溯伏笔失败: {e}")
        return f"❌ 追溯伏笔失败: {e}\n提示：请先运行 'novel-agent build-graph' 构建图数据库"


def read_multiple_files(paths: str) -> str:
    """批量读取多个文件（性能优化）

    一次性读取多个文件，减少 API 调用次数

    Args:
        paths: 文件路径列表，用逗号分隔（如 "ch1.md,ch2.md,ch3.md"）

    Returns:
        所有文件的内容，格式化为易读的字符串

    Raises:
        FileNotFoundError: 某个文件不存在
    """
    path_list = [p.strip() for p in paths.split(",")]
    logger.info(f"批量读取 {len(path_list)} 个文件")

    results = []
    for path in path_list:
        try:
            content = read_file(path)
            results.append(f"=== {path} ===\n{content}\n")
        except FileNotFoundError:
            logger.warning(f"文件不存在，跳过: {path}")
            results.append(f"=== {path} ===\n❌ 文件不存在\n")

    return "\n".join(results)


# 工具装饰器包装（用于 LangChain）
read_multiple_files_tool = lc_tool(read_multiple_files)


# ============================================================================
# 写作模板工具
# ============================================================================


def list_templates(category: str | None = None) -> str:
    """列出所有可用的写作模板

    Args:
        category: 可选的分类过滤（scene/dialogue/action/psychology/transition）

    Returns:
        格式化的模板列表

    Example:
        >>> list_templates()
        >>> list_templates(category="action")
    """
    templates_dir = Path("spec/templates")
    if not templates_dir.exists():
        return "❌ 模板目录不存在：spec/templates/"

    # 获取所有模板文件
    template_files = sorted(templates_dir.glob("*.md"))
    if not template_files:
        return "❌ 未找到任何模板文件"

    templates = []
    for file_path in template_files:
        try:
            # 解析 frontmatter
            with open(file_path, encoding="utf-8") as f:
                post = frontmatter.load(f)

            template_name = file_path.stem
            template_category = post.get("category", "unknown")
            template_description = post.get("description", "")

            # 分类过滤
            if category and template_category != category:
                continue

            templates.append(
                {
                    "name": template_name,
                    "category": template_category,
                    "description": template_description,
                    "display_name": post.get("name", template_name),
                }
            )
        except Exception as e:
            logger.warning(f"解析模板失败 {file_path}: {e}")
            continue

    if not templates:
        if category:
            return f"❌ 未找到分类为 '{category}' 的模板"
        return "❌ 未找到任何有效模板"

    # 格式化输出
    lines = ["可用的写作模板：\n"]
    if category:
        lines[0] = f"可用的写作模板（分类：{category}）：\n"

    # 按分类分组
    by_category: dict[str, list[dict[str, str]]] = {}
    for t in templates:
        cat = t["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(t)

    for cat, temps in sorted(by_category.items()):
        lines.append(f"## {cat.upper()}")
        for t in temps:
            lines.append(f"- **{t['name']}**: {t['display_name']}")
            if t["description"]:
                lines.append(f"  {t['description']}")
        lines.append("")

    return "\n".join(lines)


def apply_template(template_name: str, variables: dict[str, str]) -> str:
    """应用写作模板，使用提供的变量替换模板中的占位符

    Args:
        template_name: 模板名称（不含 .md 后缀）
        variables: 变量字典，key 为变量名，value 为替换值

    Returns:
        替换后的文本内容

    Example:
        >>> apply_template("scene-description", {
        ...     "time": "黄昏",
        ...     "location": "荒凉的战场上",
        ...     "weather": "乌云密布"
        ... })
    """
    templates_dir = Path("spec/templates")
    template_file = templates_dir / f"{template_name}.md"

    if not template_file.exists():
        available = list_templates()
        return f"❌ 模板不存在：{template_name}\n\n{available}"

    try:
        # 解析模板
        with open(template_file, encoding="utf-8") as f:
            post = frontmatter.load(f)

        content: str = str(post.content)

        # 提取模板内容（去掉使用示例部分）
        if "---\n\n**使用示例**：" in content:
            content = content.split("---\n\n**使用示例**：")[0].strip()

        # 变量替换
        for key, value in variables.items():
            pattern = rf"\$\{{{key}\}}"
            content = re.sub(pattern, value, content)

        # 检查是否还有未替换的变量
        remaining_vars = re.findall(r"\$\{([^}]+)\}", content)
        if remaining_vars:
            logger.warning(f"模板中有未替换的变量: {remaining_vars}")
            content += f"\n\n⚠️  以下变量未提供值：{', '.join(remaining_vars)}"

        return content.strip()

    except Exception as e:
        logger.error(f"应用模板失败: {e}")
        return f"❌ 应用模板失败：{str(e)}"


# ==================== 风格指南系统 ====================


def check_style_compliance(chapter_number: int) -> str:
    """检查章节是否符合风格指南要求

    Args:
        chapter_number: 章节编号

    Returns:
        格式化的检查报告（Markdown）
    """
    from pathlib import Path

    import yaml

    try:
        # 读取风格指南
        style_guide_path = Path("spec/style-guide.yaml")
        if not style_guide_path.exists():
            return "❌ 错误：找不到 spec/style-guide.yaml 风格指南文件"

        with open(style_guide_path, encoding="utf-8") as f:
            style_guide = yaml.safe_load(f)

        # 读取章节内容
        chapter_file = Path(f"chapters/chapter_{chapter_number}.md")
        if not chapter_file.exists():
            return f"❌ 错误：找不到第 {chapter_number} 章文件"

        with open(chapter_file, encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")

        # 检查报告
        report = [f"# 第{chapter_number}章风格检查报告\n"]

        # 1. 检查禁用词汇
        forbidden_issues = []
        forbidden_words = style_guide.get("forbidden_words", [])
        for line_num, line in enumerate(lines, 1):
            for rule in forbidden_words:
                word = rule["word"]
                if word in line:
                    suggestions = ", ".join(
                        f'"{s}"' if s else "(删除)" for s in rule["suggestions"][:3]
                    )
                    forbidden_issues.append(
                        f'- 第{line_num}行："{line.strip()}" → 含有 "{word}" '
                        f"({rule['reason']})\\n  建议: {suggestions}"
                    )

        if forbidden_issues:
            report.append(f"## ❌ 禁用词汇（{len(forbidden_issues)}处）\n")
            report.extend(forbidden_issues)
            report.append("")
        else:
            report.append("## ✅ 禁用词汇：通过\n")

        # 2. 检查角色语气
        voice_issues = []
        character_voice = style_guide.get("character_voice", {})
        for line_num, line in enumerate(lines, 1):
            # 检测对话（简单实现：包含冒号或引号）
            if "：" in line or '"' in line or "「" in line:
                for char_name, char_rules in character_voice.items():
                    if char_name in line:
                        # 检查是否使用了禁用词汇
                        for forbidden in char_rules.get("forbidden", []):
                            if forbidden in line:
                                voice_issues.append(
                                    f'- 第{line_num}行：{char_name}说 "{line.strip()}" '
                                    f'→ 含有不符合角色设定的词汇 "{forbidden}"\\n'
                                    f"  {char_name}的语气应为：{char_rules['tone']}"
                                )

        if voice_issues:
            report.append(f"## ⚠️  角色语气不一致（{len(voice_issues)}处）\n")
            report.extend(voice_issues)
            report.append("")
        else:
            report.append("## ✅ 角色语气：通过\n")

        # 3. 检查标点符号
        punct_issues = []
        punct_rules = style_guide.get("punctuation_rules", {})

        # 检查感叹号数量
        exclaim_count = content.count("！")
        exclaim_limit = punct_rules.get("exclamation_limit", 5)
        if exclaim_count > exclaim_limit:
            punct_issues.append(f"- 感叹号过多：{exclaim_count}处（限制：{exclaim_limit}处）")

        # 检查省略号格式
        if "..." in content:
            punct_issues.append(
                f"- 省略号格式错误：应使用 \"{punct_rules.get('ellipsis_format', '……')}\""
                ' 而非 "..."'
            )

        if punct_issues:
            report.append(f"## ⚠️  标点符号规范（{len(punct_issues)}处）\n")
            report.extend(punct_issues)
            report.append("")
        else:
            report.append("## ✅ 标点符号规范：通过\n")

        # 4. 检查句式风格
        style_issues = []
        sentence_style = style_guide.get("sentence_style", {})
        max_length = sentence_style.get("max_length", 50)

        for line_num, line in enumerate(lines, 1):
            # 检查句子长度（简单实现：按句号分割）
            sentences = [s for s in line.split("。") if s.strip()]
            for sent in sentences:
                if len(sent) > max_length:
                    style_issues.append(
                        f"- 第{line_num}行：句子过长（{len(sent)}字，限制{max_length}字）"
                    )

        if style_issues:
            report.append(f"## ⚠️  句式风格（{len(style_issues)}处）\n")
            report.extend(style_issues)
            report.append("")
        else:
            report.append("## ✅ 句式风格：通过\n")

        # 总结
        total_issues = (
            len(forbidden_issues) + len(voice_issues) + len(punct_issues) + len(style_issues)
        )
        if total_issues == 0:
            report.append("\n## 🎉 总结\n\n所有检查项均通过！")
        else:
            report.append(f"\n## 📊 总结\n\n发现 {total_issues} 处需要改进的地方。")

        return "\n".join(report)

    except Exception as e:
        logger.error(f"风格检查失败: {e}")
        return f"❌ 风格检查失败：{str(e)}"


def apply_style_fix(chapter_number: int, auto_fix: bool = False) -> str:
    """应用风格修复建议

    Args:
        chapter_number: 章节编号
        auto_fix: 是否自动修复（True=自动修复，False=仅显示建议）

    Returns:
        修复报告或建议列表
    """
    from pathlib import Path

    import yaml

    try:
        # 读取风格指南
        style_guide_path = Path("spec/style-guide.yaml")
        if not style_guide_path.exists():
            return "❌ 错误：找不到 spec/style-guide.yaml 风格指南文件"

        with open(style_guide_path, encoding="utf-8") as f:
            style_guide = yaml.safe_load(f)

        # 读取章节内容
        chapter_file = Path(f"chapters/chapter_{chapter_number}.md")
        if not chapter_file.exists():
            return f"❌ 错误：找不到第 {chapter_number} 章文件"

        with open(chapter_file, encoding="utf-8") as f:
            content = f.read()

        if not auto_fix:
            # 仅显示建议
            report = check_style_compliance(chapter_number)
            return f"{report}\n\n💡 提示：使用 auto_fix=True 参数可自动应用修复建议"

        # 自动修复
        modified = content
        fixes_applied = []

        # 1. 修复禁用词汇（使用第一个建议）
        forbidden_words = style_guide.get("forbidden_words", [])
        for rule in forbidden_words:
            word = rule["word"]
            suggestions = rule.get("suggestions", [])
            if suggestions and suggestions[0]:  # 使用第一个非空建议
                replacement = suggestions[0]
                count = modified.count(word)
                if count > 0:
                    modified = modified.replace(word, replacement)
                    fixes_applied.append(f'- 替换 "{word}" → "{replacement}" ({count}处)')
            elif word in modified:  # 如果第一个建议是空（删除）
                count = modified.count(word)
                modified = modified.replace(word, "")
                fixes_applied.append(f'- 删除 "{word}" ({count}处)')

        # 2. 修复省略号格式
        punct_rules = style_guide.get("punctuation_rules", {})
        ellipsis_format = punct_rules.get("ellipsis_format", "……")
        if "..." in modified:
            count = modified.count("...")
            modified = modified.replace("...", ellipsis_format)
            fixes_applied.append(f"- 修复省略号格式 ({count}处)")

        # 保存修改
        if fixes_applied:
            with open(chapter_file, "w", encoding="utf-8") as f:
                f.write(modified)

            fix_report: list[str] = [
                f"# 第{chapter_number}章风格修复报告\n",
                f"## ✅ 已应用修复（{len(fixes_applied)}项）\n",
            ]
            fix_report.extend(fixes_applied)
            fix_report.append("\n## 📝 提示\n")
            fix_report.append("- 文件已保存")
            fix_report.append("- 建议重新运行检查确认效果")
            return "\n".join(fix_report)
        else:
            return f"第{chapter_number}章没有可自动修复的问题。"

    except Exception as e:
        logger.error(f"风格修复失败: {e}")
        return f"❌ 风格修复失败：{str(e)}"


# ==================== 大纲生成器 ====================


def generate_outline(
    genre: str,
    target_words: int,
    themes: list[str],
    style: str = "爽文",
) -> str:
    """根据题材自动生成三幕结构大纲

    Args:
        genre: 题材（玄幻、都市、科幻、武侠、历史、言情）
        target_words: 目标字数
        themes: 主题列表
        style: 风格（爽文、虐文、轻松、严肃）

    Returns:
        格式化的大纲文本（Markdown）
    """
    try:
        # 计算章节数（假设每章1000字）
        words_per_chapter = 1000
        total_chapters = max(target_words // words_per_chapter, 10)

        # 三幕分配（起10%、承转70%、合20%）
        act1_chapters = max(int(total_chapters * 0.1), 5)
        act3_chapters = max(int(total_chapters * 0.2), 10)
        act2_chapters = total_chapters - act1_chapters - act3_chapters

        act1_words = act1_chapters * words_per_chapter
        act2_words = act2_chapters * words_per_chapter
        act3_words = act3_chapters * words_per_chapter

        # 主题文本
        themes_text = "、".join(themes)

        # 生成大纲
        outline = [
            f"# {genre}小说大纲（{target_words}字，约{total_chapters}章）\n",
            "## 基本信息\n",
            f"- **题材**：{genre}",
            f"- **风格**：{style}",
            f"- **主题**：{themes_text}",
            f"- **目标字数**：{target_words}字",
            f"- **章节数**：{total_chapters}章（每章约{words_per_chapter}字）\n",
            f"## 第一幕：建立世界观（1-{act1_chapters}章，{act1_words}字）\n",
            "### 核心目标",
            "- 引入主角和世界观",
            "- 建立冲突和动机",
            "- 展示主角初始能力\n",
            "### 章节分配",
            f"- **第1章**：开篇，主角登场（{words_per_chapter}字）",
            "  - 情节点：介绍主角背景和现状",
            "  - 冲突：引入初始矛盾",
            "",
            f"- **第{act1_chapters // 2}章**：事件触发，主角卷入（{words_per_chapter}字）",
            "  - 情节点：关键事件发生",
            "  - 转折：主角被迫改变",
            "",
            f"- **第{act1_chapters}章**：第一幕结束，进入新世界（{words_per_chapter}字）",
            "  - 情节点：主角踏上旅程",
            "  - 结果：离开舒适区\n",
            (
                f"## 第二幕：冲突升级（{act1_chapters + 1}-"
                f"{act1_chapters + act2_chapters}章，{act2_words}字）\n"
            ),
            "### 核心目标",
            "- 主角成长和历练",
            "- 引入更大的冲突",
            "- 情节不断升级\n",
            "### 关键情节点",
            f"- **第{act1_chapters + act2_chapters // 4}章**：第一次失败，遭遇强敌",
            f"- **第{act1_chapters + act2_chapters // 2}章**：转折点，获得机缘或发现真相",
            f"- **第{act1_chapters + act2_chapters * 3 // 4}章**：情节升级，面临重大选择",
            f"- **第{act1_chapters + act2_chapters}章**：第二幕结束，准备最终决战\n",
            (
                f"## 第三幕：高潮与结局（{act1_chapters + act2_chapters + 1}-"
                f"{total_chapters}章，{act3_words}字）\n"
            ),
            "### 核心目标",
            "- 最终决战",
            "- 解决所有冲突",
            "- 角色成长完成\n",
            "### 章节分配",
            f"- **第{act1_chapters + act2_chapters + act3_chapters // 2}章**：最终决战开始",
            f"- **第{total_chapters - 2}章**：高潮，决定性时刻",
            f"- **第{total_chapters}章**：大结局，开启新篇章\n",
            "## 角色成长弧线\n",
            "1. **起点**：普通人/弱者",
            "2. **觉醒**：发现天赋/使命",
            "3. **成长**：历练和突破",
            "4. **转折**：面临失败和挫折",
            "5. **蜕变**：克服困难，达成目标",
            "6. **终点**：成为强者，完成使命\n",
            "## 创作建议\n",
            f"- **节奏**：{style}风格，注意情节起伏",
            f"- **主题**：围绕{themes_text}展开",
            "- **冲突**：确保每个阶段都有明确的矛盾",
            "- **成长**：主角能力和心理要有明显变化",
        ]

        return "\n".join(outline)

    except Exception as e:
        logger.error(f"大纲生成失败: {e}")
        return f"❌ 大纲生成失败：{str(e)}"


# 工具装饰器包装（用于 LangChain）
list_templates_tool = lc_tool(list_templates)
apply_template_tool = lc_tool(apply_template)
check_style_compliance_tool = lc_tool(check_style_compliance)
apply_style_fix_tool = lc_tool(apply_style_fix)
generate_outline_tool = lc_tool(generate_outline)

# 创意工具包装
dialogue_enhancer_tool = lc_tool(dialogue_enhancer)
plot_twist_generator_tool = lc_tool(plot_twist_generator)
scene_transition_tool = lc_tool(scene_transition)
