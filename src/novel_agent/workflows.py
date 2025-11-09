"""Predefined LangGraph workflows for Novel Agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langgraph.graph import END, StateGraph

from . import nervus_cli
from .continuity import build_continuity_index
from .tools import verify_strict_references, verify_strict_timeline


class ChapterState(TypedDict, total=False):
    prompt: str
    outline: str
    draft: str
    issues: str
    context: str


def build_chapter_workflow(
    model: Runnable[Any, Any],
    *,
    continuity_index: dict[str, Any] | None = None,
    index_path: Path | None = None,
    nervus_db: str | None = None,
) -> Any:  # 返回 StateGraph 的编译版本
    """Create a simple chapter-writing workflow."""

    data = continuity_index or build_continuity_index(Path.cwd(), output_path=index_path)
    builder = StateGraph(ChapterState)

    gather_chain = (
        ChatPromptTemplate.from_messages(
            [
                ("system", "你是资料整理助手，整合背景设定"),
                (
                    "human",
                    "用户需求:\n{prompt}\n\n已有章节摘要:\n{outline}\n\n外部资料:\n{context}",
                ),
            ]
        )
        | model
    )

    def gather_node(state: ChapterState) -> ChapterState:
        prompt = state.get("prompt", "")
        outline_fragments = []
        for chapter in data.get("chapters", [])[:5]:
            outline_fragments.append(
                f"- {chapter['chapter_id']}: {chapter['summary']} "
                f"(时间标记 {len(chapter.get('time_markers', []))})"
            )
        outline_text = "\n".join(outline_fragments)

        context_text = ""
        if nervus_db:
            try:
                resp = nervus_cli.cypher_query(
                    nervus_db,
                    "MATCH (c:Character) RETURN c.name as name LIMIT 5",
                )
                rows = resp.get("rows") if isinstance(resp, dict) else resp
                context_text = json.dumps(rows, ensure_ascii=False)
            except Exception:
                context_text = ""

        response = gather_chain.invoke(
            {
                "prompt": prompt,
                "outline": outline_text or "暂无章节摘要",
                "context": context_text or "",
            }
        )
        content = response.content if isinstance(response, AIMessage) else str(response)
        return {"outline": str(content), "context": context_text}

    builder.add_node("gather", gather_node)

    draft_chain = (
        ChatPromptTemplate.from_messages(
            [
                ("system", "根据资料写一个章节草稿"),
                (
                    "human",
                    "资料:\n{outline}\n\n请输出章节草稿，包含描写、冲突、悬念。",
                ),
            ]
        )
        | model
    )

    def draft_node(state: ChapterState) -> ChapterState:
        response = draft_chain.invoke({"outline": state.get("outline", "")})
        content = response.content if isinstance(response, AIMessage) else str(response)
        return {"draft": str(content)}

    builder.add_node("draft", draft_node)

    def verify_node(state: ChapterState) -> ChapterState:
        timeline = verify_strict_timeline()
        references = verify_strict_references()
        issues = []

        # 新格式：errors/warnings 是 dict 列表
        if timeline["errors"]:
            issues.append("时间线错误:")
            for err in timeline["errors"]:
                file = err.get("file", "")
                line = err.get("line", 0)
                msg = err.get("message", "")
                suggestion = err.get("suggestion", "")
                issues.append(f"  - [{file}:{line}] {msg}")
                if suggestion:
                    issues.append(f"    建议: {suggestion}")

        if timeline["warnings"]:
            issues.append("时间线警告:")
            for warn in timeline["warnings"]:
                file = warn.get("file", "")
                line = warn.get("line", 0)
                msg = warn.get("message", "")
                issues.append(f"  - [{file}:{line}] {msg}")

        if references["errors"]:
            issues.append("引用错误:")
            for err in references["errors"]:
                file = err.get("file", "")
                line = err.get("line", 0)
                msg = err.get("message", "")
                suggestion = err.get("suggestion", "")
                issues.append(f"  - [{file}:{line}] {msg}")
                if suggestion:
                    issues.append(f"    建议: {suggestion}")

        if references["warnings"]:
            issues.append("引用警告:")
            for warn in references["warnings"]:
                file = warn.get("file", "")
                line = warn.get("line", 0)
                msg = warn.get("message", "")
                issues.append(f"  - [{file}:{line}] {msg}")

        return {"issues": "\n".join(issues) or "未发现严重问题"}

    builder.add_node("verify", verify_node)

    builder.set_entry_point("gather")
    builder.add_edge("gather", "draft")
    builder.add_edge("draft", "verify")
    builder.add_edge("verify", END)

    return builder.compile()


__all__ = ["build_chapter_workflow"]
