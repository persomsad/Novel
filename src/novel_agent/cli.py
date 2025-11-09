"""CLI interface for novel-agent

使用 Typer + Rich 创建命令行界面
"""

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Optional

import typer
from langchain_google_genai import ChatGoogleGenerativeAI
from prompt_toolkit import PromptSession
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from . import memory_ingest as memory_ingest_module
from .agent import AGENT_CONFIGS, create_novel_agent, create_specialized_agent
from .continuity import build_continuity_index
from .logging_config import get_logger
from .permissions import get_readonly_tools
from .session_store import delete_session, open_checkpointer
from .session_store import list_sessions as list_session_ids
from .workflows import build_chapter_workflow

logger = get_logger(__name__)

app = typer.Typer(
    name="novel-agent",
    help="AI写作助手 - 基于LangChain + Gemini的智能小说创作工具",
    add_completion=False,
)
console = Console()


def format_error(error: Exception) -> str:
    """格式化错误消息为友好提示

    Args:
        error: 异常对象

    Returns:
        格式化的错误消息
    """
    from .error_handler import (
        APIKeyError,
        find_similar_files,
    )

    error_msg = str(error)

    # API Key 错误
    if "api" in error_msg.lower() and "key" in error_msg.lower():
        err = APIKeyError()
        return err.format_message()

    # 文件不存在错误
    if isinstance(error, FileNotFoundError) or "no such file" in error_msg.lower():
        # 尝试从错误消息中提取文件路径
        import re

        match = re.search(r"['\"](.*?)['\"]", error_msg)
        if match:
            file_path = match.group(1)
            similar = find_similar_files(file_path, ".", limit=3)

            lines = [f"❌ 文件不存在: {file_path}\n"]
            if similar:
                lines.append("💡 建议：")
                lines.append("  是否要查找相似文件？")
                for file in similar:
                    lines.append(f"    找到: {file}")
                lines.append(f"  或创建新文件: novel-agent write {file_path}")
            else:
                lines.append("💡 建议：")
                lines.append(f"  创建新文件: novel-agent write {file_path}")
            return "\n".join(lines)

    # 网络错误
    if any(
        keyword in error_msg.lower()
        for keyword in ["network", "connection", "timeout", "unreachable"]
    ):
        lines = [
            f"❌ 网络错误: {error_msg}\n",
            "💡 建议：",
            "  - 检查网络连接",
            "  - 检查防火墙/代理设置",
            "  - 稍后重试",
        ]
        return "\n".join(lines)

    # 默认错误消息
    return f"❌ 错误: {error_msg}"


@app.command()
def refresh_memory(
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="输出路径（默认为 data/continuity/index.json）",
    ),
) -> None:
    """生成连续性索引（章节→角色→时间标记→引用）。"""

    output_path = Path(output) if output else Path("data/continuity/index.json")
    console.print(
        Panel.fit(
            "[bold cyan]🔁 刷新连续性索引[/bold cyan]\n" f"输出: [yellow]{output_path}[/yellow]",
            border_style="cyan",
        )
    )

    try:
        with console.status("[yellow]正在解析章节与设定...[/yellow]"):
            data = build_continuity_index(Path.cwd(), output_path=output_path)
        console.print(
            f"[green]✓[/green] 已生成 {len(data['chapters'])} 章、"
            f"{len(data['characters'])} 角色、{len(data['references'])} 引用的索引"
        )
    except Exception as exc:
        console.print(f"[red]✗ 生成失败: {exc}[/red]")
        raise typer.Exit(code=1) from exc


@app.command()
def build_graph(
    chapters_dir: str = typer.Option(
        "chapters",
        "--chapters-dir",
        "-c",
        help="章节目录路径",
    ),
    db_path: str = typer.Option(
        "data/novel-graph.nervusdb",
        "--db-path",
        "-d",
        help="图数据库文件路径",
    ),
    clear: bool = typer.Option(
        False,
        "--clear",
        help="清空旧图数据（危险操作！）",
    ),
) -> None:
    """构建知识图谱（从章节内容提取实体和关系）。"""

    from .graph_ingest import build_graph_from_chapters

    console.print(
        Panel.fit(
            "[bold cyan]🔨 构建知识图谱[/bold cyan]\n"
            f"章节目录: [yellow]{chapters_dir}[/yellow]\n"
            f"数据库: [yellow]{db_path}[/yellow]",
            border_style="cyan",
        )
    )

    if clear:
        console.print("[yellow]⚠️  清空旧图数据...[/yellow]")
        from .graph_ingest import GraphBuilder

        builder = GraphBuilder(db_path)
        builder.clear_graph()
        console.print("[green]✓ 已清空[/green]")

    try:
        with console.status("[yellow]正在解析章节和构建图...[/yellow]"):
            stats = build_graph_from_chapters(chapters_dir, db_path)

        console.print("\n[green]✓ 图构建完成！[/green]")
        console.print(f"  - 处理章节: {stats['chapters_processed']}")
        console.print(f"  - 创建实体: {stats['entities_created']}")
        console.print(f"  - 创建关系: {stats['relations_created']}")

        if stats["errors"]:
            console.print(f"\n[yellow]⚠️  遇到 {len(stats['errors'])} 个错误：[/yellow]")
            for err in stats["errors"][:5]:
                console.print(f"  - {err}")

    except Exception as exc:
        console.print(f"[red]✗ 构建失败: {exc}[/red]")
        raise typer.Exit(code=1) from exc


@app.command()
def chat(
    prompt: Optional[str] = typer.Argument(None, help="提示词（仅在 --print 模式下使用）"),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        "-k",
        help="Gemini API Key（可选，默认从环境变量GOOGLE_API_KEY读取）",
    ),
    prompt_file: Optional[str] = typer.Option(
        None,
        "--file",
        "-f",
        help="从文件读取 Prompt",
    ),
    variables: Optional[list[str]] = typer.Option(
        None,
        "--var",
        help="变量替换（格式：KEY=value）",
    ),
    agent: str = typer.Option(
        "default",
        "--agent",
        "-a",
        help=f"Agent类型（可选值: {', '.join(AGENT_CONFIGS.keys())}）",
    ),
    session: Optional[str] = typer.Option(
        None,
        "--session",
        "-s",
        help="会话ID（如果需要继续之前的对话）",
    ),
    enable_watcher: bool = typer.Option(
        True,
        "--enable-watcher/--disable-watcher",
        help="启用/禁用文件监控（默认启用）",
    ),
    enable_context: bool = typer.Option(
        True,
        "--enable-context/--disable-context",
        help="启用/禁用自动上下文检索（默认启用）",
    ),
    print_mode: bool = typer.Option(
        False,
        "--print",
        "-p",
        help="非交互模式：打印结果后退出（用于脚本和管道）",
    ),
    output_format: str = typer.Option(
        "text",
        "--output-format",
        help="输出格式：text（默认）、json、stream-json",
    ),
    stream: bool = typer.Option(
        False,
        "--stream",
        help="流式输出：实时显示 LLM 生成过程",
    ),
    no_cache: bool = typer.Option(
        False,
        "--no-cache",
        help="禁用缓存（默认启用）",
    ),
    read_only: bool = typer.Option(
        False,
        "--read-only",
        help="只读模式（仅允许读取和分析，不允许编辑）",
    ),
    # 保留旧参数但标记为 deprecated
    allowed_tools: Optional[str] = typer.Option(
        None,
        "--allowed-tools",
        help="[已废弃] 请使用 --read-only。允许使用的工具列表（逗号分隔，白名单）",
    ),
    disallowed_tools: Optional[str] = typer.Option(
        None,
        "--disallowed-tools",
        help="[已废弃] 请使用 --read-only。禁止使用的工具列表（逗号分隔，黑名单）",
    ),
    tools_mode: str = typer.Option(
        "default",
        "--tools",
        help=(
            "[已废弃] 请使用 --read-only。"
            "工具模式：default（所有工具）、minimal（只读工具）、custom（自定义）"
        ),
    ),
    input_offset: Optional[int] = typer.Option(
        None,
        "--input-offset",
        help="输入框向上偏移行数（默认：自动适应终端高度，通常 5-8 行）",
    ),
) -> None:
    """启动对话模式

    示例:
        novel-agent chat
        novel-agent chat --agent outline-architect
        novel-agent chat --api-key YOUR_API_KEY --agent outline-architect
        novel-agent chat --print '检查第3章一致性'
        novel-agent chat --print --output-format json '检查一致性'
    """

    # 初始化缓存
    from .cache import disable_cache, enable_cache

    cache_manager = None
    if not no_cache:
        cache_manager = enable_cache()
        logger.debug("缓存已启用")
    else:
        disable_cache()
        logger.debug("缓存已禁用")

    # 显示废弃警告
    if allowed_tools or disallowed_tools or tools_mode != "default":
        console.print(
            "[yellow]⚠️  --tools、--allowed-tools 和 --disallowed-tools 参数已废弃[/yellow]\n"
            "[yellow]   推荐使用更简单的权限系统：[/yellow]\n"
            "[yellow]   • 默认模式（所有工具）：novel-agent chat[/yellow]\n"
            "[yellow]   • 只读模式（仅分析）：novel-agent chat --read-only[/yellow]\n"
        )

    # 解析工具权限参数
    allowed_tools_list = None
    disallowed_tools_list = None

    if read_only:
        # 只读模式：只允许读取和分析工具
        allowed_tools_list = get_readonly_tools()
    elif allowed_tools:
        # 旧的白名单方式（兼容）
        allowed_tools_list = [t.strip() for t in allowed_tools.split(",")]
    elif disallowed_tools:
        # 旧的黑名单方式（兼容）
        disallowed_tools_list = [t.strip() for t in disallowed_tools.split(",")]
    # else: 默认模式，允许所有工具（allowed_tools_list = None）

    # 计算输入框偏移（用于交互模式）
    calculated_offset = input_offset if input_offset is not None else _get_optimal_input_offset()

    # 处理从文件读取 Prompt
    file_prompt = None
    if prompt_file:
        from .prompt_loader import load_prompt_from_file, parse_variables

        try:
            # 解析变量
            variables_dict = parse_variables(variables) if variables else None

            # 加载 Prompt
            file_prompt = load_prompt_from_file(prompt_file, variables_dict)

            console.print(f"[green]✓[/green] 从文件加载 Prompt: [cyan]{prompt_file}[/cyan]")
            if variables_dict:
                console.print(f"[green]✓[/green] 变量替换: {len(variables_dict)} 个变量")

        except FileNotFoundError as e:
            console.print(f"[red]错误：{e}[/red]")
            raise typer.Exit(1) from e
        except Exception as e:
            console.print(f"[red]错误：加载 Prompt 文件失败: {e}[/red]")
            raise typer.Exit(1) from e

    # 处理非交互模式
    if print_mode:
        # 验证输出格式
        valid_formats = ["text", "json", "stream-json"]
        if output_format not in valid_formats:
            console.print(
                f"[red]错误：无效的输出格式 '{output_format}'[/red]\n"
                f"有效选项: {', '.join(valid_formats)}"
            )
            raise typer.Exit(1)

        # 获取输入（优先级：文件 > 参数 > 管道）
        if file_prompt:
            user_input = file_prompt
        elif prompt:
            user_input = prompt
        elif not sys.stdin.isatty():
            # 从管道读取
            user_input = sys.stdin.read().strip()
        else:
            console.print(
                "[red]错误：--print 模式需要提示词或从管道输入[/red]\n"
                "示例: novel-agent chat --print '你的问题'\n"
                "示例: novel-agent chat --print -f prompts/check.md\n"
                "或: echo '你的问题' | novel-agent chat --print"
            )
            raise typer.Exit(1)

        if not user_input:
            console.print("[red]错误：输入为空[/red]")
            raise typer.Exit(1)

        # 执行单次查询（非交互模式的逻辑稍后实现）
        _run_print_mode(
            user_input,
            agent,
            api_key,
            output_format,
            enable_watcher,
            enable_context,
            stream,
            cache_manager,
            allowed_tools_list,
            disallowed_tools_list,
            tools_mode,
        )
        return

    # 交互模式：显示Agent类型
    agent_name = agent if agent != "default" else "通用写作助手"
    console.print(
        Panel.fit(
            f"[bold cyan]🤖 Novel Agent[/bold cyan]\n"
            f"AI写作助手已启动 - [yellow]{agent_name}[/yellow]\n\n"
            "[dim]输入 'exit' 或按 Ctrl+C 退出[/dim]",
            border_style="cyan",
        )
    )

    session_id = session or str(uuid.uuid4())
    console.print(f"[cyan]Session ID[/cyan]: [bold]{session_id}[/bold]")

    # 获取项目根目录
    project_root = Path.cwd()

    # 启动性能跟踪器
    from .performance_tracker import get_tracker

    tracker = get_tracker()
    tracker.reset()
    tracker.start()

    # 启动文件监控（如果启用）
    watcher_thread = None
    if enable_watcher:
        try:
            from .file_watcher import start_background_watcher

            index_path = project_root / "data" / "continuity" / "index.json"
            watcher_thread = start_background_watcher(project_root, index_path)
            console.print("[green]✓[/green] 文件监控已启动（后台模式）\n")
        except Exception as e:
            console.print(f"[yellow]⚠️  文件监控启动失败: {e}[/yellow]")

    try:
        with open_checkpointer() as checkpointer:
            with console.status("[yellow]正在初始化Agent...[/yellow]"):
                agent_instance = create_specialized_agent(
                    agent,
                    api_key=api_key,
                    checkpointer=checkpointer,
                    enable_context_retrieval=enable_context,
                    project_root=str(project_root) if enable_context else None,
                    allowed_tools=allowed_tools_list,
                    disallowed_tools=disallowed_tools_list,
                    tools_mode=tools_mode,
                )

            if enable_context:
                console.print("[green]✓[/green] Agent初始化完成（自动上下文检索已启用）\n")
            else:
                console.print("[green]✓[/green] Agent初始化完成\n")

            # 如果有文件 prompt，先执行
            if file_prompt:
                console.print("[cyan]执行文件 Prompt...[/cyan]\n")
                with console.status("[yellow]正在思考...[/yellow]"):
                    result = agent_instance.invoke(
                        {"messages": [("user", file_prompt)]},
                        config={"configurable": {"thread_id": session_id}},
                    )

                if "messages" in result and result["messages"]:
                    last_message = result["messages"][-1]
                    response = (
                        last_message.content
                        if hasattr(last_message, "content")
                        else str(last_message)
                    )

                    # 显示置信度评分
                    confidence = result.get("confidence", 0)
                    confidence_color = (
                        "green" if confidence >= 80 else "yellow" if confidence >= 60 else "red"
                    )
                    confidence_icon = (
                        "🟢" if confidence >= 80 else "🟡" if confidence >= 60 else "🔴"
                    )

                    console.print(
                        f"\n[bold green]Agent[/bold green] "
                        f"[{confidence_color}]{confidence_icon} "
                        f"置信度: {confidence}/100[/{confidence_color}]"
                    )
                    console.print(Markdown(response))
                console.print()  # 空行

            # 显示输入框偏移提示（首次）
            if calculated_offset != 5:
                console.print(
                    f"[dim]ℹ️  输入框偏移：{calculated_offset} 行"
                    f"（可使用 --input-offset 自定义）[/dim]\n"
                )

            _chat_loop(agent_instance, session_id, input_offset=calculated_offset)

    except ValueError as e:
        console.print(format_error(e))
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 再见！[/yellow]")
    except Exception as e:
        console.print(format_error(e))
        sys.exit(1)
    finally:
        # 停止性能跟踪并显示统计
        tracker.stop()
        console.print("\n" + tracker.get_stats().format_summary())

        # 停止文件监控
        if enable_watcher and watcher_thread:
            try:
                from .file_watcher import stop_background_watcher

                stop_background_watcher()
                console.print("[dim]✓ 文件监控已停止[/dim]")
            except Exception:
                pass  # 忽略停止失败


def _get_optimal_input_offset() -> int:
    """根据终端高度计算最佳输入框偏移

    目标：输入框在屏幕 60-70% 位置（参考 Claude Desktop）
    """
    import shutil

    try:
        terminal_height = shutil.get_terminal_size().lines
    except (AttributeError, ValueError):
        # 如果无法获取终端大小，使用默认值
        return 5

    # 输入框在屏幕 65% 位置
    optimal_position = int(terminal_height * 0.65)
    offset = terminal_height - optimal_position

    # 最小 3 行，最大 10 行
    return max(3, min(10, offset))


def _handle_slash_command(user_input: str, session_id: str, agent_instance: Any) -> str | None:
    """处理斜杠命令

    Args:
        user_input: 用户输入
        session_id: 当前会话 ID
        agent_instance: Agent 实例

    Returns:
        新的 session_id（如果需要切换会话），否则返回 None
    """
    parts = user_input.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if command == "/compress":
        try:
            import asyncio

            from .session_compression import compress_session

            # 获取当前会话的历史消息
            # 从 agent state 中获取
            checkpointer = agent_instance.checkpointer
            config = {"configurable": {"thread_id": session_id}}

            # 获取当前状态
            state = checkpointer.get(config)
            if not state or "messages" not in state.get("channel_values", {}):
                console.print("[yellow]⚠️  当前会话为空，无需压缩[/yellow]")
                return None

            messages = state["channel_values"]["messages"]

            # 显示压缩提示
            console.print("\n[cyan]🔄 正在压缩会话...[/cyan]")
            console.print(f"  当前会话：{session_id}")
            console.print(f"  消息数量：{len(messages)} 条")

            # 执行压缩（获取 LLM 实例）
            llm = agent_instance.llm  # 假设 agent 有 llm 属性

            with console.status("[yellow]生成摘要中...[/yellow]"):
                new_id, summary, original_tokens, compressed_tokens = asyncio.run(
                    compress_session(messages, llm, new_prompt=args if args else None)
                )

            # 显示压缩统计
            reduction_rate = (original_tokens - compressed_tokens) / original_tokens * 100

            console.print("\n[green]✓ 会话已压缩[/green]")
            console.print(f"  原始：{original_tokens:,} tokens ({len(messages)} 条消息)")
            console.print(f"  压缩：{compressed_tokens:,} tokens (摘要)")
            console.print(f"  节省：{reduction_rate:.0f}% tokens\n")

            # 显示摘要预览
            preview = summary[:150] + "..." if len(summary) > 150 else summary
            console.print("  摘要预览：")
            console.print(f"  [dim]{preview}[/dim]\n")

            console.print(f"[green]✓ 新会话已创建：{new_id}[/green]")

            # 初始化新会话的 checkpointer
            from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

            initial_messages: list[BaseMessage] = [
                SystemMessage(content=f"上次对话摘要：\n{summary}")
            ]
            if args:
                initial_messages.append(HumanMessage(content=args))

            # 保存到新会话
            new_config = {"configurable": {"thread_id": new_id}}
            checkpointer.put(new_config, {"channel_values": {"messages": initial_messages}})

            return new_id

        except Exception as e:
            console.print(f"[red]✗ 压缩失败: {e}[/red]")
            import traceback

            traceback.print_exc()
            return None

    elif command == "/sessions":
        from .session_export import get_session_metadata, list_session_ids

        checkpointer = agent_instance.checkpointer
        session_ids = list_session_ids(checkpointer)

        if not session_ids:
            console.print("[yellow]暂无历史会话[/yellow]")
            return None

        # 显示会话列表
        console.print("\n[bold cyan]最近的会话：[/bold cyan]")
        console.print("━" * 60)

        # 只显示最近 10 个
        for i, sid in enumerate(session_ids[:10], 1):
            metadata = get_session_metadata(sid, checkpointer)
            console.print(
                f"{i}. [{metadata['created_at']}] {metadata['title']} ({sid})\n"
                f"   {metadata['message_count']} 轮对话 | "
                f"{metadata['total_tokens']} tokens"
            )

        console.print("━" * 60)

        # 用户选择
        from prompt_toolkit import prompt as pt_prompt

        choice = pt_prompt("\n输入序号继续会话，或 q 退出: ").strip()

        if choice == "q" or not choice:
            return None

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(session_ids[:10]):
                selected_id = session_ids[idx]
                console.print(f"[green]✓ 切换到会话：{selected_id}[/green]")
                return selected_id
            else:
                console.print("[yellow]⚠️  无效的序号[/yellow]")
                return None
        except ValueError:
            console.print("[yellow]⚠️  无效的输入[/yellow]")
            return None

    elif command == "/export":
        from .session_export import export_session

        checkpointer = agent_instance.checkpointer
        format = "markdown"  # 默认格式

        # 解析参数（如果有）
        if args:
            # 简单解析：/export json 或 /export txt
            if args.lower() in ["json", "txt", "markdown"]:
                format = args.lower()

        try:
            output_path = export_session(session_id, checkpointer, format=format)
            console.print(f"[green]✓ 已导出到：{output_path}[/green]")
        except Exception as e:
            console.print(f"[red]✗ 导出失败: {e}[/red]")

        return None

    elif command == "/help":
        console.print("\n[cyan]可用命令：[/cyan]")
        console.print("  /compress [新提示]  - 压缩当前会话并创建新会话")
        console.print("  /sessions           - 查看历史会话并切换")
        console.print("  /export [格式]      - 导出当前会话（格式: markdown/json/txt）")
        console.print("  /help               - 显示此帮助")
        console.print("  exit/quit/bye       - 退出对话\n")
        return None

    else:
        console.print(f"[yellow]⚠️  未知命令：{command}[/yellow]")
        console.print("  输入 /help 查看可用命令")
        return None


def _chat_loop(agent_instance: Any, session_id: str, input_offset: int = 5) -> None:
    """交互式对话循环

    Args:
        agent_instance: Agent 实例
        session_id: 会话 ID
        input_offset: 输入框向上偏移行数
    """
    # 创建 PromptSession 用于更好的输入处理（支持中文、特殊键等）
    # reserve_space_for_menu 参数让输入框向上偏移
    prompt_session: PromptSession[str] = PromptSession(reserve_space_for_menu=input_offset)

    # 当前会话 ID（可能会因为 /compress 而改变）
    current_session_id = session_id

    while True:
        try:
            # 使用 prompt_toolkit 替代 console.input()
            # 这样可以正确处理：
            # - 中文输入
            # - Backspace/Delete 键
            # - 方向键
            # - 其他特殊键
            user_input = prompt_session.prompt("\n你: ")

            if user_input.lower() in ("exit", "quit", "bye"):
                console.print("[yellow]👋 再见！[/yellow]")
                break

            if not user_input.strip():
                continue

            # 处理斜杠命令
            if user_input.startswith("/"):
                command_result = _handle_slash_command(
                    user_input, current_session_id, agent_instance
                )
                if command_result:
                    # 命令返回新的 session_id
                    current_session_id = command_result
                continue

            with console.status("[yellow]正在思考...[/yellow]"):
                result = agent_instance.invoke(
                    {"messages": [("user", user_input)]},
                    config={"configurable": {"thread_id": current_session_id}},
                )

            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                response = (
                    last_message.content if hasattr(last_message, "content") else str(last_message)
                )

                # 显示置信度评分
                confidence = result.get("confidence", 0)
                confidence_color = (
                    "green" if confidence >= 80 else "yellow" if confidence >= 60 else "red"
                )
                confidence_icon = "🟢" if confidence >= 80 else "🟡" if confidence >= 60 else "🔴"

                console.print(
                    f"\n[bold green]Agent[/bold green] "
                    f"[{confidence_color}]{confidence_icon} "
                    f"置信度: {confidence}/100[/{confidence_color}]"
                )
                console.print(Markdown(response))
            else:
                console.print("[red]✗ Agent未返回响应[/red]")

        except KeyboardInterrupt:
            console.print("\n[yellow]👋 再见！[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]✗ 错误: {e}[/red]")
            break


@app.command()
def check(
    file_pattern: str = typer.Argument(..., help="要检查的文件路径或 glob 模式"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="Gemini API Key"),
    auto_fix: bool = typer.Option(False, "--auto-fix", help="自动修复发现的问题"),
    parallel: bool = typer.Option(False, "--parallel", help="并行处理多个文件"),
    output_format: str = typer.Option("text", "--output-format", help="输出格式: text/json"),
) -> None:
    """一致性检查

    检查指定文件的一致性问题（角色、情节、时间线等）

    示例:
        novel-agent check chapters/ch001.md
        novel-agent check chapters/*.md
        novel-agent check chapters/*.md --auto-fix
        novel-agent check chapters/*.md --parallel --output-format json
    """
    import glob as glob_module
    import json as json_module
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # 解析文件列表
    files = []
    if "*" in file_pattern or "?" in file_pattern:
        # Glob 模式
        matched_files = glob_module.glob(file_pattern, recursive=True)
        files = [Path(f) for f in matched_files if Path(f).is_file()]
        if not files:
            console.print(f"[red]✗ 没有找到匹配的文件: {file_pattern}[/red]")
            raise typer.Exit(1)
    else:
        # 单个文件
        file = Path(file_pattern)
        if not file.exists():
            console.print(f"[red]✗ 文件不存在: {file_pattern}[/red]")
            raise typer.Exit(1)
        files = [file]

    # 批量模式或单文件模式
    is_batch = len(files) > 1

    if is_batch and output_format == "text":
        console.print(
            Panel.fit(
                f"[bold cyan]🔍 批量检查 {len(files)} 个文件[/bold cyan]\n"
                f"模式: [yellow]{'并行' if parallel else '顺序'}[/yellow]\n"
                f"自动修复: [yellow]{'是' if auto_fix else '否'}[/yellow]",
                border_style="cyan",
            )
        )

    # 单文件模式（保持向后兼容）
    if not is_batch:
        _check_single_file(files[0], api_key, auto_fix, output_format)
        return

    # 批量模式
    try:
        # 创建 Agent
        with console.status("[yellow]正在初始化 Agent...[/yellow]"):
            agent = create_novel_agent(api_key=api_key)

        # 统计信息
        results = []
        total_errors = 0
        total_warnings = 0
        files_with_errors = 0
        files_with_warnings = 0
        files_passed = 0

        # 批量处理
        from rich.progress import Progress

        # 是否显示进度条（JSON 模式下不显示）
        show_progress = output_format == "text"

        if parallel:
            # 并行处理
            with ThreadPoolExecutor(max_workers=min(len(files), 4)) as executor:
                future_to_file = {
                    executor.submit(_check_file_task, f, agent, auto_fix): f for f in files
                }

                if show_progress:
                    with Progress() as progress:
                        task = progress.add_task("[cyan]检查中...", total=len(files))

                        for future in as_completed(future_to_file):
                            file = future_to_file[future]
                            try:
                                result = future.result()
                                results.append(result)
                                if result["status"] == "error":
                                    files_with_errors += 1
                                    total_errors += len(result.get("issues", []))
                                elif result["status"] == "warning":
                                    files_with_warnings += 1
                                    total_warnings += len(result.get("issues", []))
                                else:
                                    files_passed += 1
                            except Exception as e:
                                results.append(
                                    {"file": str(file), "status": "error", "message": str(e)}
                                )
                                files_with_errors += 1
                            progress.update(task, advance=1)
                else:
                    # 不显示进度条
                    for future in as_completed(future_to_file):
                        file = future_to_file[future]
                        try:
                            result = future.result()
                            results.append(result)
                            if result["status"] == "error":
                                files_with_errors += 1
                                total_errors += len(result.get("issues", []))
                            elif result["status"] == "warning":
                                files_with_warnings += 1
                                total_warnings += len(result.get("issues", []))
                            else:
                                files_passed += 1
                        except Exception as e:
                            results.append(
                                {"file": str(file), "status": "error", "message": str(e)}
                            )
                            files_with_errors += 1
        else:
            # 顺序处理
            if show_progress:
                with Progress() as progress:
                    task = progress.add_task("[cyan]检查中...", total=len(files))

                    for file in files:
                        try:
                            result = _check_file_task(file, agent, auto_fix)
                            results.append(result)
                            if result["status"] == "error":
                                files_with_errors += 1
                                total_errors += len(result.get("issues", []))
                            elif result["status"] == "warning":
                                files_with_warnings += 1
                                total_warnings += len(result.get("issues", []))
                            else:
                                files_passed += 1
                        except Exception as e:
                            results.append(
                                {"file": str(file), "status": "error", "message": str(e)}
                            )
                            files_with_errors += 1
                        progress.update(task, advance=1)
            else:
                # 不显示进度条
                for file in files:
                    try:
                        result = _check_file_task(file, agent, auto_fix)
                        results.append(result)
                        if result["status"] == "error":
                            files_with_errors += 1
                            total_errors += len(result.get("issues", []))
                        elif result["status"] == "warning":
                            files_with_warnings += 1
                            total_warnings += len(result.get("issues", []))
                        else:
                            files_passed += 1
                    except Exception as e:
                        results.append({"file": str(file), "status": "error", "message": str(e)})
                        files_with_errors += 1

        # 输出结果
        if output_format == "json":
            output = {
                "total_files": len(files),
                "passed": files_passed,
                "warnings": files_with_warnings,
                "errors": files_with_errors,
                "total_warnings": total_warnings,
                "total_errors": total_errors,
                "results": results,
            }
            print(json_module.dumps(output, ensure_ascii=False, indent=2))
        else:
            # 文本格式汇总报告
            console.print(
                f"\n[bold cyan]📊 汇总报告：[/bold cyan]\n"
                f"  [green]✅ 通过: {files_passed} 个文件[/green]\n"
                f"  [yellow]⚠️  警告: {files_with_warnings} 个文件 "
                f"({total_warnings} 个警告)[/yellow]\n"
                f"  [red]❌ 错误: {files_with_errors} 个文件 ({total_errors} 个错误)[/red]"
            )

            # 显示详细问题
            if files_with_errors > 0 or files_with_warnings > 0:
                console.print("\n[bold]详细信息：[/bold]")
                for result in results:
                    if result["status"] in ["error", "warning"]:
                        icon = "❌" if result["status"] == "error" else "⚠️"
                        console.print(f"\n  {icon} [yellow]{result['file']}[/yellow]:")
                        for issue in result.get("issues", []):
                            console.print(f"    {issue}")

    except ValueError as e:
        console.print(f"[red]✗ 初始化失败: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ 错误: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def sessions(
    list_: bool = typer.Option(False, "--list", help="列出所有会话ID"),
    delete: Optional[str] = typer.Option(None, "--delete", help="删除指定会话"),
) -> None:
    """管理持久化会话。"""

    if list_:
        ids = list_session_ids()
        if not ids:
            console.print("[yellow]暂无会话记录。[/yellow]")
        else:
            console.print("[bold cyan]现有会话[/bold cyan]:")
            for sid in ids:
                console.print(f"  - {sid}")
    elif delete:
        delete_session(delete)
        console.print(f"[green]✓[/green] 已删除会话 {delete}")
    else:
        console.print("使用 --list 查看或 --delete <id> 删除会话。")


@app.command()
def memory_ingest(
    db: str = typer.Option(..., "--db", "-d", help="NervusDB 数据库文件路径"),
    index: Optional[str] = typer.Option(
        None, "--index", help="已有连续性索引路径（默认 data/continuity/index.json）"
    ),
    refresh: bool = typer.Option(True, "--refresh/--no-refresh", help="执行前是否重建索引"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅打印统计，不实际写入"),
) -> None:
    """将连续性索引写入 NervusDB（通过 CLI）。"""

    index_path = Path(index) if index else Path("data/continuity/index.json")
    try:
        if refresh or not index_path.exists():
            data = build_continuity_index(Path.cwd(), output_path=index_path)
        else:
            # If not refreshing and index exists, we need to load it.
            # Assuming there's a function to load it, or build_continuity_index
            # can also load if it exists and refresh is False.
            # Given the original error, _load_continuity_index was the problem.
            # For now, let's assume build_continuity_index handles both
            # creation and loading implicitly
            # or that the 'data' is always generated by
            # 'build_continuity_index' and returned.
            # Re-reading the refresh_memory function,
            # build_continuity_index always returns the data.
            # So, if refresh is False and index_path exists, it means we don't need to do anything
            # However, the previous code explicitly called _load_continuity_index.
            data = build_continuity_index(Path.cwd(), output_path=index_path)
    except Exception as exc:
        console.print(f"[red]✗ 索引加载失败: {exc}")
        raise typer.Exit(code=1) from exc

    try:
        with console.status("[yellow]正在写入 NervusDB...[/yellow]"):
            stats = memory_ingest_module.ingest_from_index(data, db, dry_run=dry_run)
    except Exception as exc:
        console.print(f"[red]✗ 写入失败: {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[green]✓[/green] 已处理 {stats['characters']} 角色, {stats['chapters']} 章节, "
        f"{stats['events']} 时间点, {stats['references']} 引用" + ("（dry-run）" if dry_run else "")
    )


@app.command()
def run(
    workflow: str = typer.Argument(..., help="workflow 名称，目前支持 chapter"),
    prompt: Optional[str] = typer.Option(None, "--prompt", help="章节需求描述"),
    prompt_file: Optional[str] = typer.Option(None, "--prompt-file", help="从文件读取需求"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Gemini API Key"),
    nervus_db: Optional[str] = typer.Option(None, "--nervus-db", help="NervusDB 数据库路径"),
    index: Optional[str] = typer.Option(None, "--index", help="连续性索引路径"),
    refresh: bool = typer.Option(True, "--refresh/--no-refresh", help="是否重新生成索引"),
) -> None:
    """运行预置 workflow（目前实现 chapter）。"""

    if workflow != "chapter":
        console.print("[red]暂不支持该 workflow。[red]")
        raise typer.Exit(code=1)

    if prompt_file:
        prompt_text = Path(prompt_file).read_text(encoding="utf-8")
    else:
        prompt_text = prompt or ""

    if not prompt_text.strip():
        console.print("[red]请通过 --prompt 或 --prompt-file 指定需求描述。[/red]")
        raise typer.Exit(code=1)

    index_path = Path(index) if index else Path("data/continuity/index.json")
    if refresh or not index_path.exists():
        index_data = build_continuity_index(Path.cwd(), output_path=index_path)
    else:
        # Same logic as above: build_continuity_index should return the data
        # regardless of refresh status, handling existing files.
        index_data = build_continuity_index(Path.cwd(), output_path=index_path)

    gemini_key = api_key or os.getenv("GOOGLE_API_KEY")
    if not gemini_key:
        console.print("[red]未找到 Gemini API Key，请使用 --api-key 或设置 GOOGLE_API_KEY。[/red]")
        raise typer.Exit(code=1)

    model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        google_api_key=gemini_key,
        temperature=0.6,
    )

    workflow_graph = build_chapter_workflow(
        model,
        continuity_index=index_data,
        index_path=index_path,
        nervus_db=nervus_db,
    )

    result = workflow_graph.invoke({"prompt": prompt_text})

    console.print("[bold cyan]Workflow 输出[/bold cyan]")
    console.print("[green]Outline:[/green]\n" + (result.get("outline") or "(空)"))
    console.print("[green]Draft:[/green]\n" + (result.get("draft") or "(空)"))
    console.print("[yellow]Issues:[/yellow]\n" + (result.get("issues") or "(空)"))


@app.command()
def graph_query(
    query: str = typer.Argument(..., help="查询内容（如'张三和李四的关系'）"),
    search_type: str = typer.Option(
        "all",
        "--type",
        "-t",
        help="搜索类型: character|location|event|foreshadow|all",
    ),
    max_hops: int = typer.Option(2, "--max-hops", "-m", help="最大关系跳数（1-3）"),
    limit: int = typer.Option(10, "--limit", "-l", help="最多返回结果数"),
    db_path: str = typer.Option(
        "data/novel-graph.nervusdb",
        "--db-path",
        "-d",
        help="图数据库文件路径",
    ),
) -> None:
    """智能图查询（基于 NervusDB 知识图谱）。"""

    from .tools import smart_context_search_tool

    console.print(
        Panel.fit(
            "[bold cyan]🔍 智能图查询[/bold cyan]\n"
            f"查询: [yellow]{query}[/yellow]\n"
            f"类型: [yellow]{search_type}[/yellow]",
            border_style="cyan",
        )
    )

    try:
        # 设置环境变量
        os.environ["NOVEL_GRAPH_DB"] = db_path

        with console.status("[yellow]正在查询图数据库...[/yellow]"):
            result = smart_context_search_tool(query, search_type, max_hops, limit)

        console.print("\n" + result)

    except Exception as exc:
        console.print(f"[red]✗ 查询失败: {exc}[/red]")
        console.print("\n[yellow]提示：请先运行 'novel-agent build-graph' 构建图数据库[/yellow]")
        raise typer.Exit(code=1) from exc


@app.command()
def network(
    characters: Optional[str] = typer.Option(
        None,
        "--characters",
        "-c",
        help="角色名列表（逗号分隔，留空=所有角色）",
    ),
    db_path: str = typer.Option(
        "data/novel-graph.nervusdb",
        "--db-path",
        "-d",
        help="图数据库文件路径",
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="输出 HTML 可视化文件",
    ),
) -> None:
    """分析角色关系网络。"""

    from .tools import build_character_network_tool

    console.print(
        Panel.fit(
            "[bold cyan]🕸️  角色关系网络[/bold cyan]\n"
            f"分析角色: [yellow]{characters or '所有角色'}[/yellow]",
            border_style="cyan",
        )
    )

    try:
        os.environ["NOVEL_GRAPH_DB"] = db_path

        with console.status("[yellow]正在分析关系网络...[/yellow]"):
            result = build_character_network_tool(characters)

        console.print("\n" + result)

        # 如果指定输出文件，生成 HTML 可视化
        if output:
            console.print(f"\n[yellow]生成可视化: {output}[/yellow]")
            # TODO: 实现 HTML 可视化
            console.print("[yellow]⚠️  可视化功能正在开发中...[/yellow]")

    except Exception as exc:
        console.print(f"[red]✗ 分析失败: {exc}[/red]")
        raise typer.Exit(code=1) from exc


def _handle_streaming_output(
    agent_instance: Any,
    user_input: str,
    config: dict[str, Any],
    output_format: str,
) -> None:
    """处理流式输出"""
    import json as json_module

    collected_chunks: list[str] = []
    all_messages: list[Any] = []

    try:
        # 流式调用 Agent
        for chunk in agent_instance.stream({"messages": [("user", user_input)]}, config):
            messages = chunk.get("messages", [])
            if messages:
                last_message = messages[-1]
                if hasattr(last_message, "content"):
                    content = last_message.content

                    # 收集所有消息（用于最后计算置信度）
                    all_messages = messages

                    # 如果是新内容
                    if content and (not collected_chunks or content != "".join(collected_chunks)):
                        # 计算新增的部分
                        existing_text = "".join(collected_chunks)
                        if content.startswith(existing_text):
                            new_text = content[len(existing_text) :]
                            collected_chunks.append(new_text)

                            # 根据格式输出
                            if output_format == "stream-json":
                                # 流式 JSON：每个 chunk 一行
                                chunk_data = {"chunk": new_text, "done": False}
                                print(json_module.dumps(chunk_data, ensure_ascii=False))
                                sys.stdout.flush()
                            else:
                                # text 格式：直接输出
                                print(new_text, end="", flush=True)

        # 流式输出结束
        if output_format == "stream-json":
            # 计算置信度
            from .agent import _estimate_confidence

            confidence = _estimate_confidence(all_messages) if all_messages else 0

            # 最后一个 chunk，包含置信度
            final_data = {
                "chunk": "",
                "done": True,
                "confidence": confidence,
                "response": "".join(collected_chunks),
            }
            print(json_module.dumps(final_data, ensure_ascii=False))
        elif output_format == "json":
            # JSON 格式：输出完整结果
            from .agent import _estimate_confidence

            confidence = _estimate_confidence(all_messages) if all_messages else 0
            output_data = {
                "response": "".join(collected_chunks),
                "confidence": confidence,
            }
            print("\n" + json_module.dumps(output_data, ensure_ascii=False, indent=2))
        else:
            # text 格式：换行
            print()

    except KeyboardInterrupt:
        if output_format in ["json", "stream-json"]:
            print(json_module.dumps({"error": "Interrupted", "confidence": 0}))
        raise typer.Exit(130)


def _run_print_mode(
    user_input: str,
    agent: str,
    api_key: Optional[str],
    output_format: str,
    enable_watcher: bool,
    enable_context: bool,
    stream: bool = False,
    cache_manager: Optional[Any] = None,
    allowed_tools: list[str] | None = None,
    disallowed_tools: list[str] | None = None,
    tools_mode: str = "default",
) -> None:
    """执行非交互模式的单次查询"""
    import json as json_module
    from pathlib import Path

    project_root = Path.cwd()

    # 启动文件监控（如果启用）- 但不显示消息
    watcher_thread = None
    if enable_watcher:
        try:
            from .file_watcher import start_background_watcher

            index_path = project_root / "data" / "continuity" / "index.json"
            watcher_thread = start_background_watcher(project_root, index_path)
        except Exception:
            pass  # 静默失败

    try:
        with open_checkpointer() as checkpointer:
            # 创建 Agent（不显示进度）
            agent_instance = create_specialized_agent(
                agent,
                api_key=api_key,
                checkpointer=checkpointer,
                enable_context_retrieval=enable_context,
                project_root=str(project_root) if enable_context else None,
                allowed_tools=allowed_tools,
                disallowed_tools=disallowed_tools,
                tools_mode=tools_mode,
            )

            # 执行单次查询
            import uuid

            thread_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": thread_id}}

            # 流式输出
            if stream:
                _handle_streaming_output(agent_instance, user_input, config, output_format)
                return

            # 调用 Agent（非流式）
            result = agent_instance.invoke({"messages": [("user", user_input)]}, config)

            # 提取响应
            messages = result.get("messages", [])
            if not messages:
                if output_format == "json":
                    print(json_module.dumps({"error": "No response", "confidence": 0}, indent=2))
                else:
                    print("错误：未收到响应")
                raise typer.Exit(1)

            last_message = messages[-1]
            response = (
                last_message.content if hasattr(last_message, "content") else str(last_message)
            )

            # 计算置信度
            from .agent import _estimate_confidence

            confidence = _estimate_confidence(messages)

            # 格式化输出
            if output_format == "json":
                output_data = {
                    "response": response,
                    "confidence": confidence,
                    "messages": [
                        {
                            "role": (
                                "user"
                                if hasattr(msg, "type") and msg.type == "human"
                                else "assistant"
                            ),
                            "content": (msg.content if hasattr(msg, "content") else str(msg)),
                        }
                        for msg in messages
                    ],
                }
                print(json_module.dumps(output_data, ensure_ascii=False, indent=2))
            elif output_format == "stream-json":
                # stream-json 暂时等同于 json（流式输出在 #56 实现）
                output_data = {
                    "response": response,
                    "confidence": confidence,
                }
                print(json_module.dumps(output_data, ensure_ascii=False))
            else:
                # text 格式
                print(response)

    except KeyboardInterrupt:
        if output_format == "json":
            print(json_module.dumps({"error": "Interrupted", "confidence": 0}))
        raise typer.Exit(130)
    except Exception as e:
        if output_format == "json":
            print(
                json_module.dumps({"error": str(e), "confidence": 0}, ensure_ascii=False, indent=2)
            )
        else:
            console.print(f"[red]错误：{e}[/red]")
        raise typer.Exit(1)
    finally:
        # 显示缓存统计（仅在非 JSON 格式下）
        if cache_manager and output_format == "text":
            stats = cache_manager.get_stats()
            if stats["total_queries"] > 0:
                console.print(
                    f"\n[dim]缓存命中率: {stats['hit_rate']:.1f}% "
                    f"({stats['hits']}/{stats['total_queries']})[/dim]"
                )

        # 停止文件监控
        if watcher_thread and watcher_thread.is_alive():
            try:
                watcher_thread.join(timeout=0.5)
            except Exception:
                pass


def _check_single_file(
    file: Path, api_key: Optional[str], auto_fix: bool, output_format: str
) -> None:
    """单文件检查模式（保持向后兼容）"""
    console.print(
        Panel.fit(
            f"[bold cyan]📋 一致性检查[/bold cyan]\n" f"文件: [yellow]{file}[/yellow]",
            border_style="cyan",
        )
    )

    try:
        # 创建 Agent
        with console.status("[yellow]正在初始化 Agent...[/yellow]"):
            agent = create_novel_agent(api_key=api_key)

        # 检查文件
        result = _check_file_task(file, agent, auto_fix)

        # 输出结果
        if output_format == "json":
            import json as json_module

            print(json_module.dumps(result, ensure_ascii=False, indent=2))
        else:
            if result["status"] == "passed":
                console.print("\n[bold green]✅ 检查通过[/bold green]")
            else:
                status_icon = "❌" if result["status"] == "error" else "⚠️"
                console.print(f"\n[bold]{status_icon} 发现问题：[/bold]")
                for issue in result.get("issues", []):
                    console.print(f"  {issue}")

                if auto_fix and result.get("fixed"):
                    console.print("\n[green]✅ 已自动修复问题[/green]")

    except ValueError as e:
        console.print(f"[red]✗ 初始化失败: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ 错误: {e}[/red]")
        raise typer.Exit(1)


def _check_file_task(file: Path, agent: Any, auto_fix: bool) -> dict[str, Any]:
    """检查单个文件的任务函数（用于并行处理）

    返回格式：
    {
        "file": str,
        "status": "passed" | "warning" | "error",
        "issues": list[str],
        "fixed": bool,  # 是否已修复（auto_fix 时）
    }
    """
    # 构造检查提示
    prompt = f"""请检查文件 {file} 的一致性。

分析以下方面：
1. 角色一致性：性格、能力、行为是否前后一致
2. 情节逻辑：情节发展是否合理
3. 时间线：事件顺序是否合理
4. 世界观：设定规则是否被遵守

{"并提供具体的修复方案。" if auto_fix else "请详细指出发现的问题。"}

请用以下格式返回：
- 如果没有问题：返回 "通过"
- 如果有问题：每行一个问题，格式为 "Line X: 问题描述"
"""

    try:
        # 调用 Agent
        result = agent.invoke(
            {"messages": [("user", prompt)]},
            config={"configurable": {"thread_id": f"check-{file.name}"}},
        )

        # 提取响应
        if "messages" not in result or not result["messages"]:
            return {"file": str(file), "status": "error", "issues": ["Agent 未返回响应"]}

        last_message = result["messages"][-1]
        response = last_message.content if hasattr(last_message, "content") else str(last_message)

        # 解析响应
        if "通过" in response or "no issues" in response.lower():
            return {"file": str(file), "status": "passed", "issues": []}

        # 提取问题列表
        issues = []
        for line in response.split("\n"):
            line = line.strip()
            if line and (line.startswith("Line") or line.startswith("-") or line.startswith("•")):
                issues.append(line.lstrip("-•").strip())

        # 判断严重性
        has_error = any(
            keyword in response.lower() for keyword in ["错误", "error", "critical", "严重"]
        )

        status = "error" if has_error else "warning" if issues else "passed"

        return {"file": str(file), "status": status, "issues": issues, "fixed": False}

    except Exception as e:
        return {"file": str(file), "status": "error", "issues": [f"检查失败: {str(e)}"]}


@app.command()
def memory(
    action: str = typer.Argument(..., help="操作：list/clear/search/get/save"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="记忆分类"),
    key: Optional[str] = typer.Option(None, "--key", "-k", help="记忆键"),
    value: Optional[str] = typer.Option(None, "--value", "-v", help="记忆值（JSON格式）"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="搜索关键词"),
) -> None:
    """管理长期记忆

    支持的操作：
    - list: 列出指定分类的记忆
    - clear: 清空指定分类的记忆
    - search: 搜索记忆
    - get: 获取指定记忆
    - save: 保存记忆

    示例:
        novel-agent memory list --category user_preference
        novel-agent memory save --category project_info --key protagonist --value '"李明"'
        novel-agent memory search --query 角色
        novel-agent memory clear --category user_preference
    """
    from .long_term_memory import get_memory

    memory_store = get_memory()

    if action == "list":
        if not category:
            console.print("[red]错误：list 操作需要指定 --category[/red]")
            raise typer.Exit(1)

        memories = memory_store.list_by_category(category)
        if not memories:
            console.print(f"[yellow]分类 '{category}' 中没有记忆[/yellow]")
            return

        console.print(f"[bold cyan]📚 记忆列表（{category}）：[/bold cyan]\n")
        for mem in memories:
            console.print(f"  [yellow]{mem['key']}[/yellow]: {mem['value']}")
            console.print(f"    [dim]更新时间: {mem['updated_at']}[/dim]")

    elif action == "clear":
        if not category:
            console.print("[red]错误：clear 操作需要指定 --category[/red]")
            raise typer.Exit(1)

        count = memory_store.clear_category(category)
        console.print(f"[green]✓ 已清空 {count} 条记忆（分类: {category}）[/green]")

    elif action == "search":
        if not query:
            console.print("[red]错误：search 操作需要指定 --query[/red]")
            raise typer.Exit(1)

        results = memory_store.search(query, category=category)
        if not results:
            console.print(f"[yellow]未找到匹配的记忆：{query}[/yellow]")
            return

        console.print(f"[bold cyan]🔍 搜索结果（{len(results)} 条）：[/bold cyan]\n")
        for mem in results:
            console.print(f"  [{mem['category']}] [yellow]{mem['key']}[/yellow]: {mem['value']}")

    elif action == "get":
        if not category or not key:
            console.print("[red]错误：get 操作需要指定 --category 和 --key[/red]")
            raise typer.Exit(1)

        value = memory_store.get(category, key)
        if value is None:
            console.print(f"[yellow]未找到记忆：{category}.{key}[/yellow]")
        else:
            console.print(f"[yellow]{category}.{key}[/yellow]: {value}")

    elif action == "save":
        if not category or not key or not value:
            console.print("[red]错误：save 操作需要指定 --category, --key 和 --value[/red]")
            raise typer.Exit(1)

        # 尝试解析 JSON 值
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            # 如果不是 JSON，当作字符串
            parsed_value = value

        memory_store.save(category, key, parsed_value)
        console.print(f"[green]✓ 已保存记忆：{category}.{key}[/green]")

    else:
        console.print(f"[red]错误：未知操作 '{action}'[/red]")
        console.print("支持的操作：list, clear, search, get, save")
        raise typer.Exit(1)


@app.command()
def template(
    action: str = typer.Argument(..., help="操作：list/apply"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="模板名称"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="模板分类过滤"),
    var: Optional[list[str]] = typer.Option(None, "--var", help="变量，格式：KEY=VALUE"),
) -> None:
    """管理写作模板

    支持的操作：
    - list: 列出可用模板
    - apply: 应用模板

    示例:
        novel-agent template list
        novel-agent template list --category scene
        novel-agent template apply --name scene-description --var time=黄昏 --var location=战场
    """
    from .tools import apply_template, list_templates

    if action == "list":
        # 列出模板
        result = list_templates(category=category)
        typer.echo(result)

    elif action == "apply":
        # 应用模板
        if not name:
            typer.echo("❌ 错误：apply 操作需要 --name 参数", err=True)
            raise typer.Exit(1)

        # 解析变量
        variables = {}
        if var:
            for v in var:
                if "=" not in v:
                    typer.echo(f"❌ 错误：变量格式错误 '{v}'，应为 KEY=VALUE", err=True)
                    raise typer.Exit(1)
                key, value = v.split("=", 1)
                variables[key.strip()] = value.strip()

        result = apply_template(name, variables)
        typer.echo(result)

    else:
        typer.echo(f"❌ 错误：未知操作 '{action}'，支持: list, apply", err=True)
        raise typer.Exit(1)


@app.command()
def style(
    action: str = typer.Argument(..., help="操作：check/fix"),
    chapter: int = typer.Argument(..., help="章节编号"),
    auto_fix: bool = typer.Option(False, "--auto", help="自动修复（仅限 fix 操作）"),
) -> None:
    """风格指南检查和修复

    支持的操作：
    - check: 检查章节风格
    - fix: 修复章节风格

    示例:
        novel-agent style check 1
        novel-agent style fix 1
        novel-agent style fix 1 --auto
    """
    from .tools import apply_style_fix, check_style_compliance

    if action == "check":
        # 检查风格
        result = check_style_compliance(chapter)
        typer.echo(result)

    elif action == "fix":
        # 修复风格
        result = apply_style_fix(chapter, auto_fix=auto_fix)
        typer.echo(result)

    else:
        typer.echo(f"❌ 错误：未知操作 '{action}'，支持: check, fix", err=True)
        raise typer.Exit(1)


def main() -> None:
    """Entry point for CLI"""
    app()


if __name__ == "__main__":
    main()
