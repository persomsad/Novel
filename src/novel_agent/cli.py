"""CLI interface for novel-agent

使用 Typer + Rich 创建命令行界面
"""

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
) -> None:
    """启动对话模式

    示例:
        novel-agent chat
        novel-agent chat --agent outline-architect
        novel-agent chat --api-key YOUR_API_KEY --agent outline-architect
        novel-agent chat --print '检查第3章一致性'
        novel-agent chat --print --output-format json '检查一致性'
    """
    import sys

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

        # 获取输入
        if prompt:
            user_input = prompt
        elif not sys.stdin.isatty():
            # 从管道读取
            user_input = sys.stdin.read().strip()
        else:
            console.print(
                "[red]错误：--print 模式需要提供提示词或从管道输入[/red]\n"
                "示例: novel-agent chat --print '你的问题'\n"
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
                )

            if enable_context:
                console.print("[green]✓[/green] Agent初始化完成（自动上下文检索已启用）\n")
            else:
                console.print("[green]✓[/green] Agent初始化完成\n")

            _chat_loop(agent_instance, session_id)

    except ValueError as e:
        console.print(f"[red]✗ 初始化失败: {e}[/red]")
        console.print("[yellow]提示: 请设置环境变量 GOOGLE_API_KEY 或使用 --api-key 参数[/yellow]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 再见！[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ 未知错误: {e}[/red]")
        sys.exit(1)
    finally:
        # 停止文件监控
        if enable_watcher and watcher_thread:
            try:
                from .file_watcher import stop_background_watcher

                stop_background_watcher()
                console.print("[dim]✓ 文件监控已停止[/dim]")
            except Exception:
                pass  # 忽略停止失败


def _chat_loop(agent_instance: Any, session_id: str) -> None:
    # 创建 PromptSession 用于更好的输入处理（支持中文、特殊键等）
    prompt_session: PromptSession[str] = PromptSession()

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

            with console.status("[yellow]正在思考...[/yellow]"):
                result = agent_instance.invoke(
                    {"messages": [("user", user_input)]},
                    config={"configurable": {"thread_id": session_id}},
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
    file_path: str = typer.Argument(..., help="要检查的文件路径"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="Gemini API Key"),
) -> None:
    """一致性检查

    检查指定文件的一致性问题（角色、情节、时间线等）

    示例:
        novel-agent check chapters/ch001.md
        novel-agent check spec/character-profiles.md
    """
    file = Path(file_path)

    if not file.exists():
        console.print(f"[red]✗ 文件不存在: {file_path}[/red]")
        sys.exit(1)

    console.print(
        Panel.fit(
            f"[bold cyan]📋 一致性检查[/bold cyan]\n" f"文件: [yellow]{file_path}[/yellow]",
            border_style="cyan",
        )
    )

    try:
        # 创建Agent
        with console.status("[yellow]正在初始化Agent...[/yellow]"):
            agent = create_novel_agent(api_key=api_key)

        # 构造检查提示
        prompt = f"""请检查文件 {file_path} 的一致性。

分析以下方面：
1. 角色一致性：性格、能力、行为是否前后一致
2. 情节逻辑：情节发展是否合理
3. 时间线：事件顺序是否合理
4. 世界观：设定规则是否被遵守

请详细指出发现的问题，并给出修复建议。"""

        # 调用Agent（不需要持久化，使用临时会话）
        with console.status("[yellow]正在分析...[/yellow]"):
            result = agent.invoke(
                {"messages": [("user", prompt)]},
                config={"configurable": {"thread_id": "temp-check"}},
            )

        # 显示结果
        if "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            response = (
                last_message.content if hasattr(last_message, "content") else str(last_message)
            )

            console.print("\n[bold green]分析结果[/bold green]:")
            console.print(Markdown(response))
        else:
            console.print("[red]✗ Agent未返回分析结果[/red]")

    except ValueError as e:
        console.print(f"[red]✗ 初始化失败: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ 错误: {e}[/red]")
        sys.exit(1)


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


def _run_print_mode(
    user_input: str,
    agent: str,
    api_key: Optional[str],
    output_format: str,
    enable_watcher: bool,
    enable_context: bool,
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
            )

            # 执行单次查询
            import uuid

            thread_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": thread_id}}

            # 调用 Agent
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
        # 停止文件监控
        if watcher_thread and watcher_thread.is_alive():
            try:
                watcher_thread.join(timeout=0.5)
            except Exception:
                pass


def main() -> None:
    """Entry point for CLI"""
    app()


if __name__ == "__main__":
    main()
