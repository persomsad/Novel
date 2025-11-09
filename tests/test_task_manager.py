"""测试任务管理器"""

from src.novel_agent.task_manager import TaskManager, TaskStatus


class TestTaskManager:
    """测试任务管理器"""

    def test_add_tasks(self):
        """测试添加任务"""
        tm = TaskManager()
        tm.add_tasks(["任务1", "任务2", "任务3"])

        assert len(tm.tasks) == 3
        assert tm.tasks[0].description == "任务1"
        assert tm.tasks[1].description == "任务2"
        assert tm.tasks[2].description == "任务3"
        assert all(task.status == TaskStatus.PENDING for task in tm.tasks)

    def test_mark_in_progress(self):
        """测试标记进行中"""
        tm = TaskManager()
        tm.add_tasks(["任务1", "任务2"])

        tm.mark_in_progress(0)

        assert tm.tasks[0].status == TaskStatus.IN_PROGRESS
        assert tm.tasks[1].status == TaskStatus.PENDING

    def test_mark_completed(self):
        """测试标记完成"""
        tm = TaskManager()
        tm.add_tasks(["任务1", "任务2"])

        tm.mark_completed(0)

        assert tm.tasks[0].status == TaskStatus.COMPLETED
        assert tm.tasks[1].status == TaskStatus.PENDING

    def test_render_empty(self):
        """测试渲染空任务列表"""
        tm = TaskManager()
        result = tm.render()

        assert result == ""

    def test_render_pending(self):
        """测试渲染待处理任务"""
        tm = TaskManager()
        tm.add_tasks(["读取角色设定", "读取第3章", "分析一致性"])

        result = tm.render()

        assert "任务进度：" in result
        assert "⏳ 待处理 | 读取角色设定" in result
        assert "⏳ 待处理 | 读取第3章" in result
        assert "⏳ 待处理 | 分析一致性" in result

    def test_render_in_progress(self):
        """测试渲染进行中任务"""
        tm = TaskManager()
        tm.add_tasks(["任务1", "任务2", "任务3"])
        tm.mark_in_progress(0)

        result = tm.render()

        assert "🔄 进行中 | 任务1" in result
        assert "⏳ 待处理 | 任务2" in result

    def test_render_completed(self):
        """测试渲染已完成任务"""
        tm = TaskManager()
        tm.add_tasks(["任务1", "任务2"])
        tm.mark_completed(0)

        result = tm.render()

        assert "✅ 已完成 | 任务1" in result
        assert "⏳ 待处理 | 任务2" in result

    def test_render_mixed_status(self):
        """测试渲染混合状态"""
        tm = TaskManager()
        tm.add_tasks(["任务1", "任务2", "任务3"])
        tm.mark_completed(0)
        tm.mark_in_progress(1)

        result = tm.render()

        assert "✅ 已完成 | 任务1" in result
        assert "🔄 进行中 | 任务2" in result
        assert "⏳ 待处理 | 任务3" in result

    def test_is_completed_false(self):
        """测试未完成状态"""
        tm = TaskManager()
        tm.add_tasks(["任务1", "任务2"])
        tm.mark_completed(0)

        assert not tm.is_completed()

    def test_is_completed_true(self):
        """测试全部完成状态"""
        tm = TaskManager()
        tm.add_tasks(["任务1", "任务2"])
        tm.mark_completed(0)
        tm.mark_completed(1)

        assert tm.is_completed()

    def test_is_completed_empty(self):
        """测试空任务列表"""
        tm = TaskManager()

        assert tm.is_completed()  # 空列表视为已完成

    def test_get_progress(self):
        """测试获取进度"""
        tm = TaskManager()
        tm.add_tasks(["任务1", "任务2", "任务3"])

        # 初始进度
        completed, total = tm.get_progress()
        assert completed == 0
        assert total == 3

        # 完成一个
        tm.mark_completed(0)
        completed, total = tm.get_progress()
        assert completed == 1
        assert total == 3

        # 完成全部
        tm.mark_completed(1)
        tm.mark_completed(2)
        completed, total = tm.get_progress()
        assert completed == 3
        assert total == 3

    def test_mark_invalid_task_id(self):
        """测试标记无效任务ID"""
        tm = TaskManager()
        tm.add_tasks(["任务1"])

        # 不应该抛出异常
        tm.mark_in_progress(10)
        tm.mark_completed(-1)

        # 任务状态不变
        assert tm.tasks[0].status == TaskStatus.PENDING

    def test_workflow_scenario(self):
        """测试完整工作流场景"""
        tm = TaskManager()

        # 1. 添加任务
        tm.add_tasks(["读取角色设定", "读取第3章", "分析一致性"])

        # 2. 初始状态
        result = tm.render()
        assert "⏳ 待处理 | 读取角色设定" in result

        # 3. 开始第一个任务
        tm.mark_in_progress(0)
        result = tm.render()
        assert "🔄 进行中 | 读取角色设定" in result

        # 4. 完成第一个任务
        tm.mark_completed(0)
        result = tm.render()
        assert "✅ 已完成 | 读取角色设定" in result

        # 5. 开始第二个任务
        tm.mark_in_progress(1)
        result = tm.render()
        assert "✅ 已完成 | 读取角色设定" in result
        assert "🔄 进行中 | 读取第3章" in result

        # 6. 完成所有任务
        tm.mark_completed(1)
        tm.mark_completed(2)
        assert tm.is_completed()

        completed, total = tm.get_progress()
        assert completed == 3
        assert total == 3
