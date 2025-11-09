"""测试会话导出功能"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from novel_agent.session_export import (
    export_as_json,
    export_as_markdown,
    export_as_text,
    export_session,
    get_session_history,
    get_session_metadata,
    list_session_ids,
)


@pytest.fixture
def mock_checkpointer() -> MagicMock:
    """Mock checkpointer"""
    checkpointer = MagicMock()

    # Mock list() - 返回会话列表
    checkpointer.list.return_value = [
        ({"configurable": {"thread_id": "session-1"}}, {}),
        ({"configurable": {"thread_id": "session-2"}}, {}),
    ]

    # Mock get() - 返回会话数据
    def mock_get(config: Any) -> Any:
        thread_id = config["configurable"]["thread_id"]
        if thread_id == "session-1":
            return {
                "channel_values": {
                    "messages": [
                        SystemMessage(content="系统消息"),
                        HumanMessage(content="你好"),
                        AIMessage(content="你好！有什么我可以帮助你的吗？"),
                    ]
                }
            }
        return None

    checkpointer.get.side_effect = mock_get
    return checkpointer


def test_list_session_ids(mock_checkpointer: MagicMock) -> None:
    """测试列出会话 ID"""
    session_ids = list_session_ids(mock_checkpointer)

    assert len(session_ids) == 2
    assert "session-1" in session_ids
    assert "session-2" in session_ids


def test_get_session_history(mock_checkpointer: MagicMock) -> None:
    """测试获取会话历史"""
    messages = get_session_history("session-1", mock_checkpointer)

    assert len(messages) == 3
    assert messages[0].type == "system"
    assert messages[1].type == "human"
    assert messages[2].type == "ai"


def test_get_session_history_empty(mock_checkpointer: MagicMock) -> None:
    """测试获取不存在的会话"""
    messages = get_session_history("session-999", mock_checkpointer)

    assert len(messages) == 0


def test_get_session_metadata(mock_checkpointer: MagicMock) -> None:
    """测试获取会话元数据"""
    metadata = get_session_metadata("session-1", mock_checkpointer)

    assert "created_at" in metadata
    assert "title" in metadata
    assert "message_count" in metadata
    assert "total_tokens" in metadata

    # 标题应该是第一条用户消息
    assert metadata["title"] == "你好"
    assert metadata["message_count"] == 3
    assert metadata["total_tokens"] > 0


def test_export_as_markdown() -> None:
    """测试导出为 Markdown"""
    messages = [
        SystemMessage(content="系统消息"),
        HumanMessage(content="你好"),
        AIMessage(content="你好！"),
    ]
    metadata = {
        "created_at": "2025-11-09 14:30",
        "title": "你好",
        "message_count": 3,
        "total_tokens": 100,
    }

    content = export_as_markdown("session-1", messages, metadata)

    assert "# Novel Agent 对话记录" in content
    assert "**会话 ID**: session-1" in content
    assert "**开始时间**: 2025-11-09 14:30" in content
    assert "**轮次**: 3 轮" in content
    assert "**总 Tokens**: 100" in content
    assert "### 轮次 1" in content
    assert "**你**: 你好" in content
    assert "**Agent**: 你好！" in content
    # 系统消息不应该出现
    assert "系统消息" not in content


def test_export_as_json() -> None:
    """测试导出为 JSON"""
    import json

    messages = [
        SystemMessage(content="系统消息"),
        HumanMessage(content="你好"),
        AIMessage(content="你好！"),
    ]
    metadata = {
        "created_at": "2025-11-09 14:30",
        "title": "你好",
        "message_count": 3,
        "total_tokens": 100,
    }

    content = export_as_json("session-1", messages, metadata)
    data = json.loads(content)

    assert data["session_id"] == "session-1"
    assert data["metadata"]["title"] == "你好"
    assert len(data["messages"]) == 2  # 不包含系统消息
    assert data["messages"][0]["role"] == "human"
    assert data["messages"][0]["content"] == "你好"


def test_export_as_text() -> None:
    """测试导出为纯文本"""
    messages = [
        HumanMessage(content="你好"),
        AIMessage(content="你好！"),
    ]
    metadata = {
        "created_at": "2025-11-09 14:30",
        "title": "你好",
        "message_count": 2,
        "total_tokens": 50,
    }

    content = export_as_text("session-1", messages, metadata)

    assert "Novel Agent 对话记录" in content
    assert "会话 ID: session-1" in content
    assert "[轮次 1]" in content
    assert "你: 你好" in content
    assert "Agent: 你好！" in content


def test_export_session_markdown(mock_checkpointer: MagicMock, tmp_path: Path) -> None:
    """测试导出会话（Markdown）"""
    output = tmp_path / "test.md"
    path = export_session("session-1", mock_checkpointer, output, "markdown")

    assert path.exists()
    content = path.read_text()
    assert "# Novel Agent 对话记录" in content


def test_export_session_json(mock_checkpointer: MagicMock, tmp_path: Path) -> None:
    """测试导出会话（JSON）"""
    output = tmp_path / "test.json"
    path = export_session("session-1", mock_checkpointer, output, "json")

    assert path.exists()
    import json

    data = json.loads(path.read_text())
    assert data["session_id"] == "session-1"


def test_export_session_auto_path(
    mock_checkpointer: MagicMock, tmp_path: Path, monkeypatch: Any
) -> None:
    """测试自动生成路径"""
    # 修改当前工作目录
    monkeypatch.chdir(tmp_path)

    path = export_session("session-1", mock_checkpointer, format="markdown")

    assert path.exists()
    assert path.name.startswith("session-1")
    assert path.suffix == ".markdown"
