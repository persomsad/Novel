"""任务管理可视化模块

学习 Claude Code 的 TodoWrite 功能，让用户看到 Agent 的工作进度。
适用于复杂任务（3+ 步骤）的进度追踪。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TaskStatus(Enum):
    """任务状态"""

    PENDING = "pending"  # ⏳ 待处理
    IN_PROGRESS = "in_progress"  # 🔄 进行中
    COMPLETED = "completed"  # ✅ 已完成


@dataclass
class Task:
    """单个任务"""

    id: int
    description: str
    status: TaskStatus


class TaskManager:
    """任务管理器

    用于显示复杂操作的进度，提升用户体验。

    Example:
        >>> tm = TaskManager()
        >>> tm.add_tasks([
        ...     "读取角色设定",
        ...     "读取第3章",
        ...     "分析一致性"
        ... ])
        >>> tm.render()
        任务进度：
        ⏳ 待处理 | 读取角色设定
        ⏳ 待处理 | 读取第3章
        ⏳ 待处理 | 分析一致性
        >>> tm.mark_in_progress(0)
        >>> tm.render()
        任务进度：
        🔄 进行中 | 读取角色设定
        ⏳ 待处理 | 读取第3章
        ⏳ 待处理 | 分析一致性
    """

    def __init__(self) -> None:
        self.tasks: list[Task] = []

    def add_tasks(self, descriptions: list[str]) -> None:
        """添加任务列表

        Args:
            descriptions: 任务描述列表
        """
        for i, desc in enumerate(descriptions):
            self.tasks.append(Task(id=i, description=desc, status=TaskStatus.PENDING))

    def mark_in_progress(self, task_id: int) -> None:
        """标记任务为进行中

        Args:
            task_id: 任务ID
        """
        if 0 <= task_id < len(self.tasks):
            self.tasks[task_id].status = TaskStatus.IN_PROGRESS

    def mark_completed(self, task_id: int) -> None:
        """标记任务为已完成

        Args:
            task_id: 任务ID
        """
        if 0 <= task_id < len(self.tasks):
            self.tasks[task_id].status = TaskStatus.COMPLETED

    def render(self) -> str:
        """渲染任务列表为可视化文本

        Returns:
            格式化的任务列表文本
        """
        if not self.tasks:
            return ""

        # 状态图标映射
        status_icons = {
            TaskStatus.PENDING: "⏳ 待处理",
            TaskStatus.IN_PROGRESS: "🔄 进行中",
            TaskStatus.COMPLETED: "✅ 已完成",
        }

        lines = ["任务进度："]
        for task in self.tasks:
            icon = status_icons[task.status]
            lines.append(f"{icon} | {task.description}")

        return "\n".join(lines)

    def is_completed(self) -> bool:
        """检查所有任务是否完成

        Returns:
            True 如果所有任务都完成
        """
        return all(task.status == TaskStatus.COMPLETED for task in self.tasks)

    def get_progress(self) -> tuple[int, int]:
        """获取进度统计

        Returns:
            (已完成数, 总数) 元组
        """
        completed = sum(1 for task in self.tasks if task.status == TaskStatus.COMPLETED)
        return completed, len(self.tasks)
