"""会话导出功能"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import BaseMessage
from langgraph.checkpoint.base import BaseCheckpointSaver


def list_session_ids(checkpointer: BaseCheckpointSaver[Any]) -> list[str]:
    """列出所有会话 ID

    Args:
        checkpointer: Checkpoint saver

    Returns:
        会话 ID 列表（按创建时间倒序）
    """
    # 使用 checkpointer.list() 获取所有会话
    sessions: list[str] = []
    try:
        # list() 返回 tuple (config, checkpoint, metadata, parent_config, pending_writes)
        for item in checkpointer.list(None):
            config = item[0]
            thread_id = config["configurable"].get("thread_id")
            if thread_id:
                sessions.append(thread_id)
    except Exception:
        # 如果 checkpointer 不支持 list，返回空列表
        pass

    return sessions


def get_session_history(
    session_id: str, checkpointer: BaseCheckpointSaver[Any]
) -> list[BaseMessage]:
    """获取会话历史消息

    Args:
        session_id: 会话 ID
        checkpointer: Checkpoint saver

    Returns:
        消息列表
    """
    config = {"configurable": {"thread_id": session_id}}
    checkpoint = checkpointer.get(config)  # type: ignore

    if not checkpoint:
        return []

    # 从 checkpoint 提取消息
    channel_values: dict[str, Any] = checkpoint.get("channel_values", {})
    messages: list[BaseMessage] = channel_values.get("messages", [])

    return messages


def get_session_metadata(session_id: str, checkpointer: BaseCheckpointSaver[Any]) -> dict[str, Any]:
    """获取会话元数据

    Args:
        session_id: 会话 ID
        checkpointer: Checkpoint saver

    Returns:
        元数据字典
    """
    messages = get_session_history(session_id, checkpointer)

    # 估算 token 数
    from novel_agent.session_compression import count_message_tokens

    total_tokens = count_message_tokens(messages)

    # 从 session_id 提取时间（如果是 session-{timestamp} 格式）
    created_at = "未知时间"
    if session_id.startswith("session-"):
        # 尝试解析时间戳（假设是 session-{hex} 格式）
        # 简化处理：使用第一条消息时间
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 生成会话标题（使用第一条用户消息）
    title = "未命名会话"
    for msg in messages:
        if msg.type == "human":
            content_str: str = str(msg.content)
            title = content_str[:30] + "..." if len(content_str) > 30 else content_str
            break

    return {
        "created_at": created_at,
        "title": title,
        "message_count": len(messages),
        "total_tokens": total_tokens,
    }


def export_as_markdown(
    session_id: str, messages: list[BaseMessage], metadata: dict[str, Any]
) -> str:
    """导出为 Markdown 格式

    Args:
        session_id: 会话 ID
        messages: 消息列表
        metadata: 元数据

    Returns:
        Markdown 内容
    """
    lines: list[str] = [
        "# Novel Agent 对话记录",
        "",
        f"**会话 ID**: {session_id}",
        f"**开始时间**: {metadata.get('created_at')}",
        f"**轮次**: {metadata.get('message_count')} 轮",
        f"**总 Tokens**: {metadata.get('total_tokens')}",
        "",
        "## 对话内容",
        "",
    ]

    turn = 1
    for msg in messages:
        # 跳过系统消息
        if msg.type == "system":
            continue

        role = "你" if msg.type == "human" else "Agent"
        lines.append(f"### 轮次 {turn}")
        lines.append(f"**{role}**: {msg.content}")
        lines.append("")

        if msg.type == "ai":
            turn += 1

    return "\n".join(lines)


def export_as_json(session_id: str, messages: list[BaseMessage], metadata: dict[str, Any]) -> str:
    """导出为 JSON 格式

    Args:
        session_id: 会话 ID
        messages: 消息列表
        metadata: 元数据

    Returns:
        JSON 内容
    """
    data = {
        "session_id": session_id,
        "metadata": metadata,
        "messages": [
            {"role": msg.type, "content": msg.content} for msg in messages if msg.type != "system"
        ],
    }

    return json.dumps(data, ensure_ascii=False, indent=2)


def export_as_text(session_id: str, messages: list[BaseMessage], metadata: dict[str, Any]) -> str:
    """导出为纯文本格式

    Args:
        session_id: 会话 ID
        messages: 消息列表
        metadata: 元数据

    Returns:
        文本内容
    """
    lines = [
        "Novel Agent 对话记录",
        "=" * 50,
        f"会话 ID: {session_id}",
        f"开始时间: {metadata.get('created_at')}",
        f"轮次: {metadata.get('message_count')} 轮",
        f"总 Tokens: {metadata.get('total_tokens')}",
        "=" * 50,
        "",
    ]

    turn = 1
    for msg in messages:
        if msg.type == "system":
            continue

        role = "你" if msg.type == "human" else "Agent"
        lines.append(f"[轮次 {turn}]")
        lines.append(f"{role}: {msg.content}")
        lines.append("")

        if msg.type == "ai":
            turn += 1

    return "\n".join(lines)


def export_session(
    session_id: str,
    checkpointer: BaseCheckpointSaver[Any],
    output_path: Path | None = None,
    format: str = "markdown",
) -> Path:
    """导出会话

    Args:
        session_id: 会话 ID
        checkpointer: Checkpoint saver
        output_path: 输出路径
        format: 导出格式（markdown, json, txt）

    Returns:
        导出文件路径
    """
    # 获取会话数据
    messages = get_session_history(session_id, checkpointer)
    metadata = get_session_metadata(session_id, checkpointer)

    # 生成输出路径
    if not output_path:
        timestamp = datetime.now().strftime("%Y-%m-%d")
        output_path = Path(f"exports/{session_id}-{timestamp}.{format}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 导出
    if format == "markdown":
        content = export_as_markdown(session_id, messages, metadata)
    elif format == "json":
        content = export_as_json(session_id, messages, metadata)
    else:
        content = export_as_text(session_id, messages, metadata)

    output_path.write_text(content, encoding="utf-8")
    return output_path
