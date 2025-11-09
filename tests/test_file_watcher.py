"""文件监控模块测试"""

import time
from pathlib import Path
from unittest import mock

from novel_agent.file_watcher import (
    FileWatcher,
    NovelFileHandler,
    get_file_watcher,
    start_background_watcher,
    stop_background_watcher,
)


class TestNovelFileHandler:
    """测试文件事件处理器"""

    def test_init(self, tmp_path: Path) -> None:
        """测试初始化"""
        index_path = tmp_path / "index.json"
        handler = NovelFileHandler(
            project_root=tmp_path,
            index_path=index_path,
        )

        assert handler.project_root == tmp_path
        assert handler.index_path == index_path
        assert handler.debounce_seconds == 1.0

    @mock.patch("novel_agent.file_watcher.build_continuity_index")
    def test_handle_md_file_change(self, mock_build: mock.Mock, tmp_path: Path) -> None:
        """测试处理 .md 文件变更"""
        index_path = tmp_path / "index.json"
        handler = NovelFileHandler(
            project_root=tmp_path,
            index_path=index_path,
            debounce_seconds=0.1,  # 减少测试时间
        )

        # 创建测试文件
        test_file = tmp_path / "test.md"
        test_file.write_text("test")

        # 触发修改事件
        handler._handle_file_change(str(test_file), "modified")

        # 等待防抖
        time.sleep(0.2)

        # 验证索引更新被调用
        assert mock_build.called
        mock_build.assert_called_once_with(tmp_path, output_path=index_path)

    def test_ignore_non_md_files(self, tmp_path: Path) -> None:
        """测试忽略非 .md 文件"""
        index_path = tmp_path / "index.json"
        handler = NovelFileHandler(
            project_root=tmp_path,
            index_path=index_path,
        )

        # 创建非 .md 文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        # 触发事件
        handler._handle_file_change(str(test_file), "modified")

        # pending_files 应为空
        assert len(handler._pending_files) == 0

    def test_ignore_hidden_files(self, tmp_path: Path) -> None:
        """测试忽略隐藏文件"""
        index_path = tmp_path / "index.json"
        handler = NovelFileHandler(
            project_root=tmp_path,
            index_path=index_path,
        )

        # 创建隐藏文件
        test_file = tmp_path / ".hidden.md"
        test_file.write_text("test")

        # 触发事件
        handler._handle_file_change(str(test_file), "modified")

        # pending_files 应为空
        assert len(handler._pending_files) == 0

    @mock.patch("novel_agent.file_watcher.build_continuity_index")
    def test_debounce_multiple_changes(self, mock_build: mock.Mock, tmp_path: Path) -> None:
        """测试防抖：多次修改只触发一次更新"""
        index_path = tmp_path / "index.json"
        handler = NovelFileHandler(
            project_root=tmp_path,
            index_path=index_path,
            debounce_seconds=0.2,
        )

        # 快速连续修改多个文件
        for i in range(5):
            test_file = tmp_path / f"test{i}.md"
            handler._handle_file_change(str(test_file), "modified")
            time.sleep(0.05)

        # 等待防抖完成
        time.sleep(0.3)

        # 应该只调用一次
        assert mock_build.call_count == 1

    @mock.patch("novel_agent.file_watcher.build_continuity_index")
    def test_on_update_callback(self, mock_build: mock.Mock, tmp_path: Path) -> None:
        """测试更新回调"""
        index_path = tmp_path / "index.json"

        callback_files = []

        def on_update(file_path: str) -> None:
            callback_files.append(file_path)

        handler = NovelFileHandler(
            project_root=tmp_path,
            index_path=index_path,
            on_update=on_update,
            debounce_seconds=0.1,
        )

        test_file = tmp_path / "test.md"
        handler._handle_file_change(str(test_file), "modified")

        time.sleep(0.2)

        assert len(callback_files) == 1
        assert str(test_file) in callback_files


class TestFileWatcher:
    """测试文件监控器"""

    def test_init(self, tmp_path: Path) -> None:
        """测试初始化"""
        index_path = tmp_path / "index.json"
        watcher = FileWatcher(
            project_root=tmp_path,
            index_path=index_path,
        )

        assert watcher.project_root == tmp_path
        assert watcher.index_path == index_path
        assert watcher.watch_dirs == ["chapters", "spec"]

    def test_custom_watch_dirs(self, tmp_path: Path) -> None:
        """测试自定义监控目录"""
        index_path = tmp_path / "index.json"
        watcher = FileWatcher(
            project_root=tmp_path,
            index_path=index_path,
            watch_dirs=["custom_dir"],
        )

        assert watcher.watch_dirs == ["custom_dir"]

    def test_start_daemon(self, tmp_path: Path) -> None:
        """测试后台模式启动"""
        # 创建监控目录
        (tmp_path / "chapters").mkdir()
        (tmp_path / "spec").mkdir()

        index_path = tmp_path / "index.json"
        watcher = FileWatcher(
            project_root=tmp_path,
            index_path=index_path,
        )

        # 启动后台线程
        thread = watcher.start_daemon()

        # 验证线程已启动
        assert thread.is_alive()
        assert watcher.is_running()

        # 停止监控
        watcher.stop()
        time.sleep(0.1)

        assert not watcher.is_running()

    @mock.patch("novel_agent.file_watcher.build_continuity_index")
    def test_integration_watch_file_change(self, mock_build: mock.Mock, tmp_path: Path) -> None:
        """集成测试：监控真实文件变更"""
        # 创建监控目录
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()
        (tmp_path / "spec").mkdir()

        index_path = tmp_path / "index.json"
        watcher = FileWatcher(
            project_root=tmp_path,
            index_path=index_path,
        )

        # 覆盖 debounce_seconds
        watcher.handler.debounce_seconds = 0.1

        # 启动监控
        watcher.start_daemon()
        time.sleep(0.1)  # 等待监控启动

        # 创建新文件
        test_file = chapters_dir / "ch001.md"
        test_file.write_text("# 第一章\n\n内容...")

        # 等待事件处理和防抖
        time.sleep(0.3)

        # 验证索引更新被调用
        assert mock_build.called

        # 停止监控
        watcher.stop()


class TestGlobalWatcher:
    """测试全局单例"""

    def test_get_file_watcher_singleton(self, tmp_path: Path) -> None:
        """测试单例模式"""
        index_path = tmp_path / "index.json"

        # 重置全局变量
        import novel_agent.file_watcher as fw

        fw._global_watcher = None

        # 首次获取
        watcher1 = get_file_watcher(tmp_path, index_path)

        # 再次获取（不传参）
        watcher2 = get_file_watcher()

        # 应该是同一个实例
        assert watcher1 is watcher2

        # 清理
        fw._global_watcher = None

    def test_start_background_watcher(self, tmp_path: Path) -> None:
        """测试快捷启动"""
        (tmp_path / "chapters").mkdir()
        (tmp_path / "spec").mkdir()

        index_path = tmp_path / "index.json"

        # 重置全局变量
        import novel_agent.file_watcher as fw

        fw._global_watcher = None

        # 启动后台监控
        thread = start_background_watcher(tmp_path, index_path)

        assert thread.is_alive()

        # 停止
        stop_background_watcher()

        # 清理
        fw._global_watcher = None
