"""会话压缩功能

通过 LLM 总结会话历史，创建新会话并注入摘要，节省 context 和 token
"""

import uuid
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage


def generate_session_id() -> str:
    """生成新的会话 ID"""
    return f"session-{uuid.uuid4().hex[:12]}"


def count_message_tokens(messages: list[BaseMessage]) -> int:
    """估算消息的 token 数

    简单估算：1 token ≈ 4 字符（英文）或 1.5 字符（中文）
    """
    total_chars = sum(len(str(msg.content)) for msg in messages)
    # 中文为主，按 1.5 字符/token 估算
    return int(total_chars / 1.5)


def format_messages_for_summary(messages: list[BaseMessage]) -> str:
    """格式化消息用于摘要生成"""
    formatted = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            role = "用户"
        elif isinstance(msg, AIMessage):
            role = "Agent"
        elif isinstance(msg, SystemMessage):
            continue  # 跳过系统消息
        else:
            role = "Unknown"

        content = str(msg.content)[:500]  # 限制长度
        formatted.append(f"{role}: {content}")

    return "\n\n".join(formatted)


async def generate_summary(messages: list[BaseMessage], llm: Any, target_tokens: int = 800) -> str:
    """使用 LLM 生成会话摘要

    Args:
        messages: 会话消息列表
        llm: LLM 实例
        target_tokens: 目标 token 数

    Returns:
        摘要文本
    """
    formatted_history = format_messages_for_summary(messages)

    prompt = f"""请将以下对话总结为不超过 {target_tokens} 字的摘要。

要求：
1. 保留关键决策和结论
2. 保留重要的上下文信息（角色、情节、设定等）
3. 删除闲聊和重复内容
4. 使用精炼的语言

对话历史：
{formatted_history}

请直接输出摘要（不要包含"摘要："等前缀）：
"""

    response = await llm.ainvoke(prompt)
    return str(response.content).strip()


def create_compressed_session(
    summary: str, new_prompt: str | None = None
) -> tuple[str, list[BaseMessage]]:
    """创建带摘要的新会话

    Args:
        summary: 会话摘要
        new_prompt: 可选的新提示

    Returns:
        (new_session_id, initial_messages)
    """
    new_session_id = generate_session_id()

    # 初始消息：系统消息（摘要）+ 可选的用户消息
    initial_messages: list[BaseMessage] = [SystemMessage(content=f"上次对话摘要：\n{summary}")]

    if new_prompt:
        initial_messages.append(HumanMessage(content=new_prompt))

    return new_session_id, initial_messages


async def compress_session(
    messages: list[BaseMessage],
    llm: Any,
    new_prompt: str | None = None,
    target_tokens: int = 800,
) -> tuple[str, str, int, int]:
    """压缩会话

    Args:
        messages: 当前会话消息
        llm: LLM 实例
        new_prompt: 可选的新提示
        target_tokens: 目标 token 数

    Returns:
        (new_session_id, summary, original_tokens, compressed_tokens)
    """
    # 1. 统计原始 tokens
    original_tokens = count_message_tokens(messages)

    # 2. 生成摘要
    summary = await generate_summary(messages, llm, target_tokens)

    # 3. 创建新会话
    new_session_id, initial_messages = create_compressed_session(summary, new_prompt)

    # 4. 统计压缩后的 tokens
    compressed_tokens = count_message_tokens(initial_messages)

    return new_session_id, summary, original_tokens, compressed_tokens
