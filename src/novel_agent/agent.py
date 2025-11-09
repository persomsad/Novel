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

from .context_retriever import ContextRetriever
from .tools import (
    build_character_network_tool,
    edit_chapter_lines,
    multi_edit,
    read_file,
    replace_in_file,
    search_content,
    smart_context_search_tool,
    trace_foreshadow_tool,
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

### 3. 精准编辑
你现在具备精准修改文件的能力：
- edit_chapter_lines()：修改章节的指定行（而非重写整章）
- replace_in_file()：查找替换文本（支持全部或指定第N次）
- multi_edit()：批量修改多个文件（原子性操作）

**何时使用编辑工具：**
- 用户要求"修改第X章的第Y行"
- 用户要求"把所有'张三'改成'李四'"
- 用户要求"修改多个章节中的某个内容"

**注意：**
- 编辑工具会直接修改文件，请谨慎使用
- 优先询问用户确认后再执行修改操作
- multi_edit 支持自动回滚（失败时恢复原文件）

### 4. 智能上下文检索（图数据库）⭐ 新能力
你现在具备基于知识图谱的智能检索能力（比向量检索强大 10 倍）：
- smart_context_search()：智能搜索相关上下文（多跳关系、时间线、因果推理）
- build_character_network()：构建角色关系网络（社交图谱 + 社区检测）
- trace_foreshadow()：追溯伏笔链条（setup → hints → reveal）

**为什么图 > 向量？**
- ✅ 精确关系：knows/loves/hates 等多种关系，而非单一语义相似度
- ✅ 时间感知：原生时间线，可查询"X 之前/之后发生的事"
- ✅ 多跳推理：找出"张三认识的人认识的人"
- ✅ 可解释性：清晰的图路径，而非黑盒相似度
- ✅ 零成本：本地嵌入式，无需 API 调用

**何时使用图查询：**
- 用户要求"找出张三相关的所有章节"
- 用户要求"分析角色关系网络"
- 用户要求"检查伏笔是否埋好"
- 用户要求"时间线是否一致"
- 用户要求"某个角色和哪些角色有关系"

**注意：**
- 图查询需要先运行 'novel-agent build-graph' 构建图数据库
- 图查询比文本搜索更智能，但需要数据准备
- 如果图数据库未构建，会提示用户先构建

## 约束

- 创建章节时使用 write_chapter 工具
- 修改章节特定行时使用 edit_chapter_lines 工具
- 批量替换文本时使用 replace_in_file 工具
- 批量修改多个文件时使用 multi_edit 工具
- 搜索关键词时使用 search_content 工具（简单文本搜索）
- 智能搜索时使用 smart_context_search 工具（图数据库，更智能）
- 分析角色关系时使用 build_character_network 工具
- 追溯伏笔时使用 trace_foreshadow 工具
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
            "edit_chapter_lines",
            "replace_in_file",
            "multi_edit",
            "smart_context_search",
            "build_character_network",
            "trace_foreshadow",
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
    enable_context_retrieval: bool = True,
    project_root: str | None = None,
    allowed_tools: list[str] | None = None,
    disallowed_tools: list[str] | None = None,
    tools_mode: str = "default",
) -> Any:
    """创建专业化Agent

    Args:
        agent_type: Agent类型（default, outline-architect等）
        model: LLM模型（可选，默认使用Gemini 2.0 Flash）
        api_key: Gemini API Key（可选，从环境变量读取）
        checkpointer: 会话持久化存储（可选）
        enable_context_retrieval: 是否启用自动上下文检索（默认True）
        project_root: 项目根目录（用于上下文检索）
        allowed_tools: 允许使用的工具列表（白名单）
        disallowed_tools: 禁止使用的工具列表（黑名单）
        tools_mode: 工具模式（default/minimal/custom）

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
        "edit_chapter_lines": edit_chapter_lines_tool,
        "replace_in_file": replace_in_file_tool,
        "multi_edit": multi_edit_tool,
        "smart_context_search": smart_context_search,
        "build_character_network": build_character_network,
        "trace_foreshadow": trace_foreshadow,
    }

    # 工具预设模式
    tool_presets = {
        "minimal": ["read_file", "search_content", "verify_timeline", "verify_references"],
        "default": list(tool_map.keys()),
    }

    # 确定基础工具集
    # 规则：如果没有指定任何工具权限参数，使用 Agent 配置的工具
    if allowed_tools is None and disallowed_tools is None and tools_mode == "default":
        # 默认模式：使用 Agent 配置的工具
        base_tools = config["tools"]
    elif tools_mode == "custom":
        # 自定义模式：使用 Agent 配置的工具
        base_tools = config["tools"]
    else:
        # 预设模式：使用预设的工具集
        base_tools = tool_presets.get(tools_mode, tool_presets["default"])

    # 应用白名单
    if allowed_tools is not None:
        base_tools = [t for t in base_tools if t in allowed_tools]

    # 应用黑名单
    if disallowed_tools is not None:
        base_tools = [t for t in base_tools if t not in disallowed_tools]

    # 转换为工具对象
    tools: list[BaseTool] = [tool_map[t] for t in base_tools if t in tool_map]

    # 初始化上下文检索器
    context_retriever: ContextRetriever | None = None
    if enable_context_retrieval and project_root:
        try:
            context_retriever = ContextRetriever(project_root=project_root)
        except Exception as e:
            from .logging_config import get_logger

            logger = get_logger(__name__)
            logger.warning(f"上下文检索器初始化失败: {e}")

    # 配置system message
    bound_model = model.bind(system=config["system_prompt"])

    # 创建ReAct Agent
    agent = create_react_agent(
        model=bound_model,
        tools=tools,
        checkpointer=checkpointer,
    )

    original_invoke = agent.invoke

    def invoke_with_context_and_confidence(
        input_data: dict[str, Any], *args: Any, **kwargs: Any
    ) -> Any:
        """包装 invoke：自动注入上下文 + 置信度评估"""

        # 1. 自动注入上下文
        if context_retriever and "messages" in input_data:
            messages = input_data["messages"]
            if messages:
                # 获取最后一条用户消息
                last_message = messages[-1]
                query = (
                    last_message.content if hasattr(last_message, "content") else str(last_message)
                )

                # 检索相关上下文
                try:
                    context_docs = context_retriever.retrieve_context(
                        query=query, max_tokens=8000, max_docs=3
                    )

                    if context_docs:
                        # 格式化上下文
                        context_text = context_retriever.format_context(context_docs)

                        # 将上下文添加到第一条消息（system message）
                        # 或者作为新的 system message
                        from langchain_core.messages import SystemMessage

                        context_msg = SystemMessage(content=context_text)

                        # 在用户消息前插入上下文
                        input_data["messages"] = [context_msg] + messages

                        from .logging_config import get_logger

                        logger = get_logger(__name__)
                        logger.info(f"✓ 自动注入上下文: {len(context_docs)} 个文档")

                except Exception as e:
                    from .logging_config import get_logger

                    logger = get_logger(__name__)
                    logger.warning(f"上下文检索失败: {e}")

        # 2. 调用原始 invoke
        result = original_invoke(input_data, *args, **kwargs)

        # 3. 添加置信度
        messages = result.get("messages") if isinstance(result, dict) else None
        confidence = _estimate_confidence(messages)
        if isinstance(result, dict):
            result["confidence"] = confidence

        return result

    agent.invoke = invoke_with_context_and_confidence  # type: ignore[assignment]
    return agent


def create_novel_agent(
    model: BaseChatModel | None = None,
    api_key: str | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
    allowed_tools: list[str] | None = None,
    disallowed_tools: list[str] | None = None,
    tools_mode: str = "default",
) -> Any:
    """创建小说写作Agent（向后兼容）

    Args:
        model: LLM模型（可选，默认使用Gemini 2.0 Flash）
        api_key: Gemini API Key（可选，从环境变量读取）
        checkpointer: 会话持久化存储（可选）
        allowed_tools: 允许使用的工具列表（白名单）
        disallowed_tools: 禁止使用的工具列表（黑名单）
        tools_mode: 工具模式（default/minimal/custom）

    Returns:
        ReAct Agent实例
    """
    return create_specialized_agent(
        "default",
        model,
        api_key,
        checkpointer,
        allowed_tools=allowed_tools,
        disallowed_tools=disallowed_tools,
        tools_mode=tools_mode,
    )


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
    """时间线精确验证（增强版：输出行号和修复建议）

    Returns:
        验证结果（格式化字符串，包含文件名、行号、错误类型、修复建议）
    """
    result = verify_strict_timeline()

    summary = result.get("summary", {})
    if summary.get("total_errors", 0) == 0 and summary.get("total_warnings", 0) == 0:
        return "✅ 时间线检查通过，未发现问题"

    output = []

    # 输出摘要
    output.append("📊 时间线验证摘要：")
    output.append(f"  - 错误: {summary.get('total_errors', 0)}")
    output.append(f"  - 警告: {summary.get('total_warnings', 0)}")
    output.append(f"  - 可自动修复: {'是' if summary.get('auto_fixable') else '否'}")
    output.append("")

    # 输出详细错误
    if result["errors"]:
        output.append("❌ 发现时间线错误：")
        for err in result["errors"]:
            file = err.get("file", "未知")
            line = err.get("line", 0)
            msg = err.get("message", "")
            suggestion = err.get("suggestion", "")

            output.append(f"\n  📄 {file}:{line}")
            output.append(f"     问题: {msg}")
            output.append(f"     建议: {suggestion}")

    # 输出警告
    if result["warnings"]:
        output.append("\n⚠️  时间线警告：")
        for warn in result["warnings"]:
            file = warn.get("file", "未知")
            line = warn.get("line", 0)
            msg = warn.get("message", "")
            suggestion = warn.get("suggestion", "")

            output.append(f"\n  📄 {file}:{line}")
            output.append(f"     问题: {msg}")
            output.append(f"     建议: {suggestion}")

    return "\n".join(output)


@tool
def verify_references_tool() -> str:
    """引用完整性验证（增强版：输出行号和修复建议）

    Returns:
        验证结果（格式化字符串，包含文件名、行号、错误类型、修复建议）
    """
    result = verify_strict_references()

    summary = result.get("summary", {})
    if summary.get("total_errors", 0) == 0 and summary.get("total_warnings", 0) == 0:
        return "✅ 引用检查通过，未发现问题"

    output = []

    # 输出摘要
    output.append("📊 引用验证摘要：")
    output.append(f"  - 错误: {summary.get('total_errors', 0)}")
    output.append(f"  - 警告: {summary.get('total_warnings', 0)}")
    output.append(f"  - 可自动修复: {'是' if summary.get('auto_fixable') else '否'}")
    output.append("")

    # 输出详细错误
    if result["errors"]:
        output.append("❌ 发现引用错误：")
        for err in result["errors"]:
            file = err.get("file", "未知")
            line = err.get("line", 0)
            msg = err.get("message", "")
            suggestion = err.get("suggestion", "")

            output.append(f"\n  📄 {file}:{line}")
            output.append(f"     问题: {msg}")
            output.append(f"     建议: {suggestion}")

    # 输出警告
    if result["warnings"]:
        output.append("\n⚠️  引用警告：")
        for warn in result["warnings"]:
            file = warn.get("file", "未知")
            line = warn.get("line", 0)
            msg = warn.get("message", "")
            suggestion = warn.get("suggestion", "")

            output.append(f"\n  📄 {file}:{line}")
            output.append(f"     问题: {msg}")
            output.append(f"     建议: {suggestion}")

    return "\n".join(output)


@tool
def edit_chapter_lines_tool(
    chapter_number: int, start_line: int, end_line: int, new_content: str
) -> str:
    """精准修改章节的指定行

    用于修改章节的特定行，而不是重写整个章节。
    适用场景：修改对话、调整描写、更正错误等。

    Args:
        chapter_number: 章节编号（1-999）
        start_line: 起始行号（从1开始）
        end_line: 结束行号（包含，从1开始）
        new_content: 新内容（将替换指定行）

    Returns:
        操作结果描述

    Example:
        # 修改第1章的第10-12行
        edit_chapter_lines_tool(1, 10, 12, "新的段落内容\\n可以是多行")
    """
    return edit_chapter_lines(chapter_number, start_line, end_line, new_content)


@tool
def replace_in_file_tool(
    file_path: str, search_text: str, replacement: str, occurrence: int | None = None
) -> str:
    """在文件中查找并替换文本

    用于批量替换文件中的文本，支持全部替换或指定第N次出现。
    适用场景：角色改名、地名修改、术语统一等。

    Args:
        file_path: 文件路径（如 "chapters/ch001.md"）
        search_text: 要查找的文本
        replacement: 替换文本
        occurrence: 替换第几次出现（None=全部替换，1=第一次，2=第二次...）

    Returns:
        操作结果描述

    Example:
        # 将所有"张三"替换为"李四"
        replace_in_file_tool("chapters/ch001.md", "张三", "李四")

        # 只替换第一次出现的"张三"
        replace_in_file_tool("chapters/ch001.md", "张三", "李四", 1)
    """
    return replace_in_file(file_path, search_text, replacement, occurrence)


@tool
def multi_edit_tool(operations: str) -> str:
    """批量编辑多个文件

    用于一次性修改多个文件，支持原子性操作（全部成功或全部回滚）。
    适用场景：批量角色改名、统一术语、多章节同步修改等。

    Args:
        operations: JSON格式的操作列表，例如：
            ```json
            [
                {
                    "type": "replace",
                    "file": "chapters/ch001.md",
                    "search": "张三",
                    "replace": "李四"
                },
                {
                    "type": "replace",
                    "file": "chapters/ch002.md",
                    "search": "张三",
                    "replace": "李四"
                }
            ]
            ```

    Returns:
        操作结果描述

    Note:
        如果任何一个操作失败，所有修改会自动回滚
    """
    import json

    try:
        ops_list = json.loads(operations)
        return multi_edit(ops_list)
    except json.JSONDecodeError as e:
        return f"❌ JSON格式错误: {e}"


@tool
def smart_context_search(
    query: str, search_type: str = "all", max_hops: int = 2, limit: int = 10
) -> str:
    """智能上下文搜索（基于图数据库）

    使用 NervusDB 图数据库进行智能上下文检索，比向量检索更精准、更可解释。
    通过图遍历找出所有相关内容，包括直接匹配和关系关联。

    Args:
        query: 搜索查询（如"张三和李四的关系"）
        search_type: 搜索类型
            - 'character': 只搜索角色
            - 'location': 只搜索地点
            - 'event': 只搜索事件
            - 'foreshadow': 只搜索伏笔
            - 'all': 所有类型（默认）
        max_hops: 最大关系跳数（1-3，默认 2）
        limit: 最多返回结果数（默认 10）

    Returns:
        格式化的搜索结果，包含：
        - 直接匹配的实体
        - 通过关系关联的实体
        - 图路径和置信度
        - 统计信息

    Example:
        # 搜索角色"张三"的所有相关内容
        smart_context_search("张三", "character", max_hops=2)

        # 搜索所有包含"北京"的内容
        smart_context_search("北京", "all", max_hops=1)
    """
    return smart_context_search_tool(query, search_type, max_hops, limit)


@tool
def build_character_network(character_names: str | None = None) -> str:
    """构建角色关系网络图

    分析角色之间的关系，构建社交网络图，并进行社区检测。

    Args:
        character_names: 角色名列表（逗号分隔，如"张三,李四,王五"）
                        留空则分析所有角色

    Returns:
        格式化的网络信息：
        - 节点（角色）列表
        - 边（关系）列表
        - 社区（群组）检测结果

    Example:
        # 分析所有角色的关系
        build_character_network()

        # 只分析指定角色的关系
        build_character_network("张三,李四,王五")
    """
    return build_character_network_tool(character_names)


@tool
def trace_foreshadow(foreshadow_id: str) -> str:
    """追溯伏笔完整链条

    追踪伏笔从埋下到揭晓的完整过程，帮助检查伏笔是否被正确处理。

    Args:
        foreshadow_id: 伏笔 ID（如 "foreshadow_001"）

    Returns:
        格式化的伏笔追溯结果：
        - Setup（埋笔）章节
        - Hints（暗示）列表
        - Reveal（揭晓）章节
        - 状态（已解决/未解决）

    Example:
        # 追溯伏笔 "foreshadow_001"
        trace_foreshadow("foreshadow_001")
    """
    return trace_foreshadow_tool(foreshadow_id)


def _estimate_confidence(messages: Any) -> int:
    """评估 Agent 输出的置信度（0-100）

    评分标准：
    1. 基础分（50分）：输出长度适中（50-300字）
    2. 结构化加分（30分）：
       - 有完整句子结构（10分）
       - 有条理（列表/标题）（10分）
       - 有具体建议/引用（10分）
    3. 质量加分（20分）：
       - 包含文件路径/行号（10分）
       - 包含具体示例（10分）
    4. 扣分项：
       - 错误标记（❌）：每个扣5分
       - 空洞回答（"不清楚"/"不确定"等）：扣20分
    """
    if not isinstance(messages, list) or not messages:
        return 0

    last = messages[-1]
    content = getattr(last, "content", None) or str(last)

    # 基础分：根据输出长度
    words = len(content.split())
    if words < 20:
        base_score = 20  # 太短
    elif 20 <= words <= 300:
        base_score = 50  # 适中
    else:
        base_score = 40  # 太长可能冗余

    # 结构化加分
    structure_score = 0
    sentences = content.count("。") + content.count("！") + content.count("？") + content.count(".")
    if sentences >= 3:
        structure_score += 10  # 有完整句子

    # 有列表或标题
    if any(marker in content for marker in ["- ", "* ", "1.", "2.", "##", "###"]):
        structure_score += 10

    # 有具体建议或引用
    if any(
        keyword in content
        for keyword in ["建议", "推荐", "可以", "[REF:", "[TIME:", "spec/", "chapters/"]
    ):
        structure_score += 10

    # 质量加分
    quality_score = 0
    # 包含文件路径/行号
    if any(pattern in content for pattern in [".md", "Line ", "第", "行"]):
        quality_score += 10

    # 包含具体示例
    if "```" in content or "例如" in content or "比如" in content:
        quality_score += 10

    # 扣分项
    penalty = 0
    penalty += content.count("❌") * 5  # 错误标记
    if any(
        phrase in content for phrase in ["不清楚", "不确定", "无法判断", "需要更多信息", "不知道"]
    ):
        penalty += 20  # 空洞回答

    # 计算总分
    total = base_score + structure_score + quality_score - penalty
    return max(0, min(100, total))
