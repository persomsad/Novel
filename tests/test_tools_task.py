"""任务管理工具测试"""

from novel_agent.tools_task import (
    complete_task,
    create_task_list,
    show_task_progress,
    start_task,
)


class TestTaskTools:
    """任务管理工具测试"""

    def test_create_task_list(self):
        """测试创建任务列表"""
        tasks = [
            "读取角色设定文件",
            "读取第3章内容",
            "对比分析角色行为",
        ]
        result = create_task_list.invoke({"tasks": tasks, "session_id": "test1"})

        assert "任务进度：" in result
        assert "读取角色设定文件" in result
        assert "读取第3章内容" in result
        assert "对比分析角色行为" in result
        assert "⏳" in result

    def test_start_task(self):
        """测试开始任务"""
        # 先创建任务
        tasks = ["任务1", "任务2", "任务3"]
        create_task_list.invoke({"tasks": tasks, "session_id": "test2"})

        # 开始第一个任务
        result = start_task.invoke({"task_id": 0, "session_id": "test2"})

        assert "🔄" in result
        assert "任务1" in result

    def test_complete_task(self):
        """测试完成任务"""
        # 先创建任务
        tasks = ["任务A", "任务B"]
        create_task_list.invoke({"tasks": tasks, "session_id": "test3"})

        # 开始并完成第一个任务
        start_task.invoke({"task_id": 0, "session_id": "test3"})
        result = complete_task.invoke({"task_id": 0, "session_id": "test3"})

        assert "✅" in result
        assert "任务A" in result

    def test_show_task_progress(self):
        """测试显示任务进度"""
        # 先创建任务
        tasks = ["步骤1", "步骤2", "步骤3"]
        create_task_list.invoke({"tasks": tasks, "session_id": "test4"})

        # 完成一个任务
        start_task.invoke({"task_id": 0, "session_id": "test4"})
        complete_task.invoke({"task_id": 0, "session_id": "test4"})

        # 查看进度
        result = show_task_progress.invoke({"session_id": "test4"})

        assert "进度：1/3" in result
        assert "已完成" in result

    def test_show_progress_no_tasks(self):
        """测试没有任务时显示进度"""
        result = show_task_progress.invoke({"session_id": "test_empty"})
        assert "没有活跃的任务列表" in result

    def test_task_workflow(self):
        """测试完整工作流"""
        session_id = "workflow_test"

        # 1. 创建任务列表
        tasks = ["准备材料", "开始制作", "质量检查"]
        result = create_task_list.invoke({"tasks": tasks, "session_id": session_id})
        assert "⏳" in result
        assert "准备材料" in result

        # 2. 开始第一个任务
        result = start_task.invoke({"task_id": 0, "session_id": session_id})
        assert "🔄" in result

        # 3. 完成第一个任务
        result = complete_task.invoke({"task_id": 0, "session_id": session_id})
        assert "✅" in result

        # 4. 检查进度
        result = show_task_progress.invoke({"session_id": session_id})
        assert "进度：1/3" in result

        # 5. 完成所有任务
        start_task.invoke({"task_id": 1, "session_id": session_id})
        complete_task.invoke({"task_id": 1, "session_id": session_id})
        start_task.invoke({"task_id": 2, "session_id": session_id})
        complete_task.invoke({"task_id": 2, "session_id": session_id})

        # 6. 最终进度
        result = show_task_progress.invoke({"session_id": session_id})
        assert "进度：3/3" in result
