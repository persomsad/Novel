"""CLI interface for novel-agent

使用 Typer + Rich 创建命令行界面
"""

import sys
import uuid
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from .agent import create_novel_agent

app = typer.Typer(
    name="novel-agent",
    help="AI写作助手 - 基于LangChain + Gemini的智能小说创作工具",
    add_completion=False,
)
console = Console()


@app.command()
def chat(
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        "-k",
        help="Gemini API Key（可选，默认从环境变量GOOGLE_API_KEY读取）",
    ),
) -> None:
    """启动对话模式

    示例:
        novel-agent chat
        novel-agent chat --api-key YOUR_API_KEY
    """
    console.print(
        Panel.fit(
            "[bold cyan]🤖 Novel Agent[/bold cyan]\n"
            "AI写作助手已启动\n\n"
            "[dim]输入 'exit' 或按 Ctrl+C 退出[/dim]",
            border_style="cyan",
        )
    )

    try:
        # 创建Agent
        with console.status("[yellow]正在初始化Agent...[/yellow]"):
            agent = create_novel_agent(api_key=api_key)
        console.print("[green]✓[/green] Agent初始化完成\n")

        # 对话循环
        while True:
            try:
                # 获取用户输入
                user_input = Prompt.ask("\n[bold blue]你[/bold blue]")

                if user_input.lower() in ("exit", "quit", "bye"):
                    console.print("[yellow]👋 再见！[/yellow]")
                    break

                if not user_input.strip():
                    continue

                # 调用Agent（使用会话ID保存状态）
                with console.status("[yellow]正在思考...[/yellow]"):
                    session_id = str(uuid.uuid4())
                    result = agent.invoke(
                        {"messages": [("user", user_input)]},
                        config={"configurable": {"thread_id": session_id}},
                    )

                # 显示Agent响应
                if "messages" in result and result["messages"]:
                    last_message = result["messages"][-1]
                    response = (
                        last_message.content
                        if hasattr(last_message, "content")
                        else str(last_message)
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

    except ValueError as e:
        console.print(f"[red]✗ 初始化失败: {e}[/red]")
        console.print("[yellow]提示: 请设置环境变量 GOOGLE_API_KEY 或使用 --api-key 参数[/yellow]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 再见！[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ 未知错误: {e}[/red]")
        sys.exit(1)


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


def main() -> None:
    """Entry point for CLI"""
    app()


if __name__ == "__main__":
    main()
