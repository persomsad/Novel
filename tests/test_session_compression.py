"""测试会话压缩功能"""

from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from novel_agent.session_compression import (
    compress_session,
    count_message_tokens,
    create_compressed_session,
    format_messages_for_summary,
    generate_session_id,
    generate_summary,
)


def test_generate_session_id() -> None:
    """测试会话 ID 生成"""
    session_id = generate_session_id()

    assert session_id.startswith("session-")
    assert len(session_id) == len("session-") + 12  # session- + 12 位 hex


def test_generate_session_id_unique() -> None:
    """测试会话 ID 唯一性"""
    ids = [generate_session_id() for _ in range(10)]

    assert len(set(ids)) == 10  # 所有 ID 不同


def test_count_message_tokens() -> None:
    """测试 token 计数"""
    messages = [
        HumanMessage(content="你好"),  # 2 字符 → ~1 token
        AIMessage(content="你好，有什么可以帮助你的吗？"),  # 14 字符 → ~9 tokens
    ]

    tokens = count_message_tokens(messages)

    # (2 + 14) / 1.5 ≈ 10-11 tokens
    assert 10 <= tokens <= 12


def test_count_message_tokens_empty() -> None:
    """测试空消息列表"""
    tokens = count_message_tokens([])
    assert tokens == 0


def test_format_messages_for_summary() -> None:
    """测试消息格式化"""
    messages = [
        HumanMessage(content="讨论角色"),
        AIMessage(content="好的，让我们讨论角色设定"),
        HumanMessage(content="主角性格"),
    ]

    formatted = format_messages_for_summary(messages)

    assert "用户: 讨论角色" in formatted
    assert "Agent: 好的，让我们讨论角色设定" in formatted
    assert "用户: 主角性格" in formatted


def test_format_messages_skip_system() -> None:
    """测试跳过系统消息"""
    messages = [
        SystemMessage(content="系统初始化"),
        HumanMessage(content="你好"),
        AIMessage(content="你好"),
    ]

    formatted = format_messages_for_summary(messages)

    assert "系统初始化" not in formatted
    assert "你好" in formatted


def test_format_messages_truncate_long() -> None:
    """测试截断长消息"""
    long_content = "x" * 1000
    messages = [HumanMessage(content=long_content)]

    formatted = format_messages_for_summary(messages)

    # 应该截断到 500 字符
    assert len(formatted) < 600


@pytest.mark.anyio
async def test_generate_summary() -> None:
    """测试生成摘要"""
    messages = [
        HumanMessage(content="讨论第五章的情节"),
        AIMessage(content="好的，第五章可以这样设计..."),
        HumanMessage(content="角色如何发展"),
        AIMessage(content="角色应该经历内心冲突..."),
    ]

    # Mock LLM
    mock_llm = AsyncMock()
    mock_response = Mock()
    mock_response.content = "讨论了第五章情节设计和角色发展"
    mock_llm.ainvoke.return_value = mock_response

    summary = await generate_summary(messages, mock_llm, target_tokens=800)

    assert summary == "讨论了第五章情节设计和角色发展"
    assert mock_llm.ainvoke.called


@pytest.mark.anyio
async def test_generate_summary_strips_whitespace() -> None:
    """测试摘要去除空白"""
    messages = [HumanMessage(content="测试")]

    mock_llm = AsyncMock()
    mock_response = Mock()
    mock_response.content = "  摘要内容  \n"
    mock_llm.ainvoke.return_value = mock_response

    summary = await generate_summary(messages, mock_llm)

    assert summary == "摘要内容"


def test_create_compressed_session_without_prompt() -> None:
    """测试创建压缩会话（无新提示）"""
    summary = "之前讨论了角色设定"

    session_id, messages = create_compressed_session(summary)

    assert session_id.startswith("session-")
    assert len(messages) == 1
    assert isinstance(messages[0], SystemMessage)
    assert "之前讨论了角色设定" in messages[0].content


def test_create_compressed_session_with_prompt() -> None:
    """测试创建压缩会话（带新提示）"""
    summary = "之前讨论了角色设定"
    new_prompt = "继续讨论情节"

    session_id, messages = create_compressed_session(summary, new_prompt)

    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert messages[1].content == "继续讨论情节"


@pytest.mark.anyio
async def test_compress_session() -> None:
    """测试完整压缩流程"""
    messages = [
        HumanMessage(content="讨论角色"),
        AIMessage(content="好的，角色是..."),
        HumanMessage(content="继续"),
        AIMessage(content="让我们深入探讨..."),
    ]

    # Mock LLM
    mock_llm = AsyncMock()
    mock_response = Mock()
    mock_response.content = "讨论了角色设定和特点"
    mock_llm.ainvoke.return_value = mock_response

    new_id, summary, original_tokens, compressed_tokens = await compress_session(messages, mock_llm)

    # 验证返回值
    assert new_id.startswith("session-")
    assert summary == "讨论了角色设定和特点"
    assert original_tokens > 0
    assert compressed_tokens > 0
    assert compressed_tokens < original_tokens  # 压缩后应该更少


@pytest.mark.anyio
async def test_compress_session_with_new_prompt() -> None:
    """测试压缩并执行新提示"""
    messages = [
        HumanMessage(content="讨论情节"),
        AIMessage(content="情节可以这样..."),
    ]

    mock_llm = AsyncMock()
    mock_response = Mock()
    mock_response.content = "讨论了情节设计"
    mock_llm.ainvoke.return_value = mock_response

    new_id, summary, original_tokens, compressed_tokens = await compress_session(
        messages, mock_llm, new_prompt="继续优化"
    )

    # 验证返回值
    assert original_tokens > 0
    assert compressed_tokens > 0
    # 摘要中应该包含情节相关信息
    assert "情节" in summary


@pytest.mark.anyio
async def test_compress_session_token_reduction() -> None:
    """测试 token 减少率"""
    # 创建长对话
    messages = []
    for i in range(20):
        messages.append(HumanMessage(content=f"问题 {i}: 这是一个关于角色设定的问题"))
        messages.append(AIMessage(content=f"回答 {i}: 让我详细解释这个角色的特点和发展..."))

    mock_llm = AsyncMock()
    mock_response = Mock()
    mock_response.content = "总结了 20 轮关于角色设定的讨论"
    mock_llm.ainvoke.return_value = mock_response

    new_id, summary, original, compressed = await compress_session(messages, mock_llm)

    # 验证大幅压缩
    reduction_rate = (original - compressed) / original
    assert reduction_rate > 0.5  # 至少减少 50%
