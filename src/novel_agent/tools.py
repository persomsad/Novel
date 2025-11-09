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
) -> dict[str, list[str]]:
    """时间线精确验证。"""

    data = _load_continuity_index(index_path)
    errors: list[str] = []
    warnings: list[str] = []

    def parse_date(value: str) -> datetime | None:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

    last_date: datetime | None = None
    for chapter in sorted(data.get("chapters", []), key=lambda c: c.get("chapter_id", "")):
        chapter_id = chapter.get("chapter_id")
        for marker in chapter.get("time_markers", []):
            value = marker.get("value")
            dt = parse_date(value)
            if not dt:
                warnings.append(
                    f"[{chapter_id}] 时间标记 `{value}` 无法解析 (line {marker.get('line')})"
                )
                continue
            if last_date and dt < last_date:
                errors.append(f"[{chapter_id}] 时间 `{value}` 早于上一事件 ({last_date.date()})")
            last_date = dt

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
                    if (cid, value) not in db_set:
                        errors.append(f"[{cid}] 时间 `{value}` 未写入 NervusDB")

            extra = db_set - local_set
            for cid, value in sorted(extra):
                warnings.append(f"NervusDB 中存在未在章节出现的时间 `{value}` (chapter {cid})")
        except RuntimeError as exc:
            warnings.append(str(exc))

    return {"errors": errors, "warnings": warnings}


def verify_strict_references(
    index_path: Path | None = None,
    *,
    db_path: str | None = None,
) -> dict[str, list[str]]:
    """引用完整性验证。"""

    data = _load_continuity_index(index_path)
    errors: list[str] = []
    warnings: list[str] = []

    reference_map = {ref["id"]: ref["occurrences"] for ref in data.get("references", [])}
    for ref_id, occurrences in reference_map.items():
        if not occurrences:
            warnings.append(f"引用 `{ref_id}` 无任何章节使用。")

    defined = set(reference_map.keys())
    for chapter in data.get("chapters", []):
        chapter_id = chapter.get("chapter_id")
        for ref in chapter.get("references", []):
            ref_id = ref.get("id")
            if ref_id not in defined:
                errors.append(f"[{chapter_id}] 引用 `{ref_id}` 未定义 (line {ref.get('line')})")

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
                    if (cid, ref_id) not in db_set:
                        errors.append(f"[{cid}] 引用 `{ref_id}` 未写入 NervusDB")

            extra_refs = db_set - local_refs
            for cid, ref_id in sorted(extra_refs):
                warnings.append(f"NervusDB 中存在未在章节使用的引用 `{ref_id}` (chapter {cid})")
        except RuntimeError as exc:
            warnings.append(str(exc))

    return {"errors": errors, "warnings": warnings}
