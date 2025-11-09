"""任务管理工具

为 Agent 提供任务可视化能力，让用户看到工作进度。
"""

from langchain_core.tools import tool

from .task_manager import TaskManager

# 全局 TaskManager 实例（每个会话一个）
_task_managers: dict[str, TaskManager] = {}


def get_task_manager(session_id: str = "default") -> TaskManager:
    """获取或创建 TaskManager 实例

    Args:
        session_id: 会话ID

    Returns:
        TaskManager 实例
    """
    if session_id not in _task_managers:
        _task_managers[session_id] = TaskManager()
    return _task_managers[session_id]


@tool
def create_task_list(tasks: list[str], session_id: str = "default") -> str:
    """创建任务列表（用于复杂操作）

    当你需要执行多步骤操作时（3+ 步骤），使用此工具创建任务列表，
    让用户看到你的工作计划和进度。

    Args:
        tasks: 任务描述列表，按执行顺序排列
        session_id: 会话ID（默认 "default"）

    Returns:
        格式化的任务列表

    Example:
        >>> create_task_list([
        ...     "读取角色设定文件",
        ...     "读取第3章内容",
        ...     "对比分析角色行为",
        ...     "生成问题报告"
        ... ])
        任务进度：
        ⏳ 待处理 | 读取角色设定文件
        ⏳ 待处理 | 读取第3章内容
        ⏳ 待处理 | 对比分析角色行为
        ⏳ 待处理 | 生成问题报告
    """
    tm = get_task_manager(session_id)
    tm.tasks = []  # 清空旧任务
    tm.add_tasks(tasks)
    return tm.render()


@tool
def start_task(task_id: int, session_id: str = "default") -> str:
    """开始执行某个任务

    Args:
        task_id: 任务ID（从 0 开始）
        session_id: 会话ID（默认 "default"）

    Returns:
        更新后的任务列表
    """
    tm = get_task_manager(session_id)
    tm.mark_in_progress(task_id)
    return tm.render()


@tool
def complete_task(task_id: int, session_id: str = "default") -> str:
    """完成某个任务

    Args:
        task_id: 任务ID（从 0 开始）
        session_id: 会话ID（默认 "default"）

    Returns:
        更新后的任务列表
    """
    tm = get_task_manager(session_id)
    tm.mark_completed(task_id)
    return tm.render()


@tool
def show_task_progress(session_id: str = "default") -> str:
    """显示当前任务进度

    Args:
        session_id: 会话ID（默认 "default"）

    Returns:
        当前任务列表
    """
    tm = get_task_manager(session_id)
    if not tm.tasks:
        return "当前没有活跃的任务列表"

    progress = tm.render()
    completed, total = tm.get_progress()
    return f"{progress}\n\n进度：{completed}/{total} 已完成"
