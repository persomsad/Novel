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
def chat(
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
) -> None:
    """启动对话模式

    示例:
        novel-agent chat
        novel-agent chat --agent outline-architect
        novel-agent chat --api-key YOUR_API_KEY --agent outline-architect
    """
    # 显示Agent类型
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

    try:
        with open_checkpointer() as checkpointer:
            with console.status("[yellow]正在初始化Agent...[/yellow]"):
                agent_instance = create_specialized_agent(
                    agent, api_key=api_key, checkpointer=checkpointer
                )
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


def _chat_loop(agent_instance: Any, session_id: str) -> None:
    # 创建 PromptSession 用于更好的输入处理（支持中文、特殊键等）
    prompt_session = PromptSession()

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

                console.print("\n[bold green]Agent[/bold green]:")
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


def main() -> None:
    """Entry point for CLI"""
    app()


if __name__ == "__main__":
    main()
