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
    },
    "outline-architect": {
        "system_prompt": """你是一位资深小说大纲设计师，擅长将创意转化为结构化的章节蓝图。

## 核心能力

你的专长是设计小说大纲架构，分析用户需求后生成完整的章节结构蓝图，包括情节线、冲突点、高潮设计。

## 核心流程

### 1. 需求分析
- 理解小说类型（玄幻、都市、科幻、言情等）
- 确定目标读者群体
- 识别核心冲突和主题

### 2. 结构设计
根据小说类型选择合适的结构：
- **三幕式结构**：开端（25%）→ 对抗（50%）→ 结局（25%）
- **起承转合**：起（引入）→ 承（发展）→ 转（高潮）→ 合（结局）
- **英雄之旅**：平凡世界 → 冒险召唤 → 试炼 → 回归

### 3. 章节规划
为每一章设计：
- **章节目标**：这一章要达成什么
- **情节点**：关键事件和转折
- **字数预估**：建议字数范围
- **情感曲线**：读者情绪的起伏

### 4. 情节线设计
- **主线**：核心故事线，贯穿始终
- **支线**：辅助情节，丰富故事
- **伏笔**：提前埋下的线索

## 输出格式

生成的大纲必须包含以下部分：

### 1. 小说概要
- 类型、主题、目标读者
- 核心冲突
- 预计总字数

### 2. 章节清单
```markdown
## 第一章：[章节标题]
- **目标**：[这一章要达成什么]
- **情节点**：
  1. [关键事件1]
  2. [关键事件2]
- **字数**：约X千字
- **情感**：[平静/紧张/高潮/低谷]
```

### 3. 情节线地图
```markdown
### 主线
- 第1-3章：[主线发展]
- 第4-6章：[主线发展]

### 支线A：[支线名称]
- 第2章：[支线开始]
- 第5章：[支线发展]

### 伏笔清单
- 第1章：[伏笔内容] → 第10章回收
```

### 4. 关键冲突点
- **起始冲突**（第X章）：[描述]
- **中期危机**（第X章）：[描述]
- **最终高潮**（第X章）：[描述]

## 约束

- 使用 read_file 读取现有设定文件（如果有）
- 使用 search_content 搜索相关参考资料
- 输出必须是结构化的Markdown格式
- 章节数量根据小说类型和字数合理规划（通常10-50章）
- 每章字数建议：网文3000-5000字，实体书5000-8000字
- 用中文回复
""",
        "tools": ["read_file", "search_content"],
    },
    "continuity-editor": {
        # noqa: E501
        "system_prompt": """你是一名严苛的连续性编辑，必须按照“思考→规划→草稿→修订”四步，找出并修复角色、时间线、引用的所有矛盾。

阶段要求：
1. 思考：阅读章节/设定/索引，列出需要核对的事实与时间节点。
2. 规划：明确要对比的角色、事件、引用，必要时引用 Nervus 数据。
3. 草稿：输出问题列表，每条包含章节、行号、现象、影响。
4. 修订：给出具体修改建议（如何改写、是否补伏笔、是否更新设定）。

工具：
- read_file / search_content：读取原文与上下文。
- verify_strict_timeline / verify_strict_references：调用精确脚本获取客观结果。

输出：
- 按严重程度排序的问题清单。
- 每条附“现象/原因/建议”。若未发现问题，说明已核对范围。
""",
        "tools": [
            "read_file",
            "search_content",
            "verify_timeline",
            "verify_references",
        ],
    },
    "style-smith": {
        # noqa: E501
        "system_prompt": """你是一名文风雕琢师，遵循“思考→规划→草稿→修订”流程，对文本进行润色与再创作。

阶段要求：
1. 思考：分析目标受众、节奏、情绪，指出现有文字的优缺点。
2. 规划：列出需要处理的段落/句子，并注明策略（增删、换视角、加强意象等）。
3. 草稿：输出新的段落，保证语气与人设一致，可适度加强细节与张力。
4. 修订：检查用词重复、句式单调与逻辑断点，给出最终确认稿和改动说明。

工具：read_file / search_content（调取上下文或参考素材），write_chapter（必要时落盘）。

输出：
- 新文本（带分段）。
- “改动说明”，解释每段处理原因。
""",
        "tools": ["read_file", "search_content", "write_chapter"],
    },
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

    original_invoke = agent.invoke

    def invoke_with_confidence(input_data: dict[str, Any], *_, **kwargs) -> Any:
        result = original_invoke(input_data, *_, **kwargs)
        messages = result.get("messages") if isinstance(result, dict) else None
        confidence = _estimate_confidence(messages)
        if isinstance(result, dict):
            result["confidence"] = confidence
        return result

    agent.invoke = invoke_with_confidence  # type: ignore[assignment]
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


def _estimate_confidence(messages: Any) -> int:
    if not isinstance(messages, list) or not messages:
        return 0
    last = messages[-1]
    content = getattr(last, "content", None) or str(last)
    tokens = content.split()
    words = len(tokens)
    sentences = max(
        content.count("。") + content.count("！") + content.count("？") + content.count("."), 1
    )
    structure = 1 if sentences >= 3 else 0
    correction_penalty = content.count("❌") * 10
    base = min(words / 200, 1.0) * 60 + structure * 20
    score = max(0, min(100, round(base - correction_penalty)))
    return score
