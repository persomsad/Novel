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
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from . import nervus_cli
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


def _load_continuity_index(path: Path | None = None) -> dict[str, Any]:
    target = path or Path("data/continuity/index.json")
    if not target.exists():
        raise FileNotFoundError(
            f"连续性索引 {target} 不存在。请先运行 `poetry run novel-agent refresh-memory`。"
        )
    return json.loads(target.read_text(encoding="utf-8"))


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
