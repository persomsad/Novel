"""ReAct Agent Implementation

使用 LangChain + LangGraph 创建 ReAct Agent
"""

import os
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool, tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.prebuilt import create_react_agent

from .tools import (
    read_file,
    search_content,
    verify_strict_references,
    verify_strict_timeline,
    write_chapter,
)

# Agent配置注册表
AGENT_CONFIGS = {
    "default": {
        "system_prompt": """你是一个小说写作助手，具有强大的推理和分析能力。

## 核心能力

### 1. 一致性检查（你自己的推理能力）
当用户要求检查一致性时，你应该：
1. 先读取相关设定文件（character-profiles.md、world-setting.md）
2. 再读取需要检查的章节
3. 通过对比分析，识别矛盾
4. 提供详细的问题描述和修复建议

**检查类型**：
- 角色一致性：性格、行为、能力是否前后一致
- 情节逻辑：情节发展是否合理，有无逻辑漏洞
- 时间线：事件顺序是否合理（语义层面）
- 世界观：设定规则是否被遵守

**注意**：
- 你不需要调用专门的"检查工具"
- 直接用 read_file 读取内容，然后自己分析
- 你的推理能力足以发现语义层面的矛盾

### 2. 精确验证（脚本兜底）
对于需要精确计算的情况，可以调用：
- verify_strict_timeline()：时间线精确验证（数字、日期）
- verify_strict_references()：引用完整性验证（伏笔ID）

## 约束

- 创建章节时使用 write_chapter 工具
- 搜索关键词时使用 search_content 工具
- 读取文件时使用 read_file 工具
- 始终提供具体、可操作的建议
- 用中文回复
""",
        "tools": [
            "read_file",
            "write_chapter",
            "search_content",
            "verify_timeline",
            "verify_references",
        ],
    }
}

# 向后兼容
SYSTEM_PROMPT = AGENT_CONFIGS["default"]["system_prompt"]


def create_specialized_agent(
    agent_type: str = "default",
    model: BaseChatModel | None = None,
    api_key: str | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> Any:
    """创建专业化Agent

    Args:
        agent_type: Agent类型（default, outline-architect等）
        model: LLM模型（可选，默认使用Gemini 2.0 Flash）
        api_key: Gemini API Key（可选，从环境变量读取）
        checkpointer: 会话持久化存储（可选）

    Returns:
        ReAct Agent实例
    """
    # 获取Agent配置
    if agent_type not in AGENT_CONFIGS:
        raise ValueError(f"未知的Agent类型: {agent_type}。可用类型: {list(AGENT_CONFIGS.keys())}")

    config = AGENT_CONFIGS[agent_type]

    # 配置LLM
    if model is None:
        gemini_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not gemini_key:
            raise ValueError(
                "未找到 Gemini API Key。请设置环境变量 GOOGLE_API_KEY 或通过 api_key 参数传入。"
            )

        model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=gemini_key,
            temperature=0.7,
        )

    # 根据配置选择工具
    tool_map = {
        "read_file": read_file_tool,
        "write_chapter": write_chapter_tool,
        "search_content": search_content_tool,
        "verify_timeline": verify_timeline_tool,
        "verify_references": verify_references_tool,
    }

    tools: list[BaseTool] = [tool_map[t] for t in config["tools"]]

    # 配置system message
    bound_model = model.bind(system=config["system_prompt"])

    # 创建ReAct Agent
    agent = create_react_agent(
        model=bound_model,
        tools=tools,
        checkpointer=checkpointer,
    )

    return agent


def create_novel_agent(
    model: BaseChatModel | None = None,
    api_key: str | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> Any:
    """创建小说写作Agent（向后兼容）

    Args:
        model: LLM模型（可选，默认使用Gemini 2.0 Flash）
        api_key: Gemini API Key（可选，从环境变量读取）
        checkpointer: 会话持久化存储（可选）

    Returns:
        ReAct Agent实例
    """
    return create_specialized_agent("default", model, api_key, checkpointer)


# ========== Tool Wrappers ==========


@tool
def read_file_tool(path: str) -> str:
    """读取文件内容

    Args:
        path: 文件路径

    Returns:
        文件内容
    """
    return read_file(path)


@tool
def write_chapter_tool(number: int, content: str) -> str:
    """创建新章节

    Args:
        number: 章节编号（1-999）
        content: 章节内容

    Returns:
        创建的文件路径
    """
    return write_chapter(number, content)


@tool
def search_content_tool(keyword: str) -> str:
    """搜索关键词

    Args:
        keyword: 搜索关键词

    Returns:
        匹配结果（格式化字符串）
    """
    results = search_content(keyword)
    if not results:
        return f"未找到包含 '{keyword}' 的内容"

    # 格式化输出
    output = [f"找到 {len(results)} 个匹配结果：\n"]
    for i, r in enumerate(results[:10], 1):  # 最多显示 10 个结果
        output.append(f"{i}. {r['file']}:{r['line']} - {r['content']}")

    if len(results) > 10:
        output.append(f"\n... 还有 {len(results) - 10} 个结果")

    return "\n".join(output)


@tool
def verify_timeline_tool() -> str:
    """时间线精确验证

    Returns:
        验证结果（格式化字符串）
    """
    result = verify_strict_timeline()
    if not result["errors"] and not result["warnings"]:
        return "✅ 时间线检查通过，未发现问题"

    output = []
    if result["errors"]:
        output.append("❌ 发现时间线错误：")
        output.extend(f"  - {e}" for e in result["errors"])

    if result["warnings"]:
        output.append("⚠️  时间线警告：")
        output.extend(f"  - {w}" for w in result["warnings"])

    return "\n".join(output)


@tool
def verify_references_tool() -> str:
    """引用完整性验证

    Returns:
        验证结果（格式化字符串）
    """
    result = verify_strict_references()
    if not result["errors"] and not result["warnings"]:
        return "✅ 引用检查通过，未发现问题"

    output = []
    if result["errors"]:
        output.append("❌ 发现引用错误：")
        output.extend(f"  - {e}" for e in result["errors"])

    if result["warnings"]:
        output.append("⚠️  引用警告：")
        output.extend(f"  - {w}" for w in result["warnings"])

    return "\n".join(output)
