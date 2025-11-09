"""文件监控模块

使用 watchdog 监控 chapters/ 和 spec/ 目录的文件变更，
自动触发索引更新，保持上下文始终最新。
"""

import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .continuity import build_continuity_index
from .logging_config import get_logger

logger = get_logger(__name__)


class NovelFileHandler(FileSystemEventHandler):
    """处理小说项目文件变更事件"""

    def __init__(
        self,
        project_root: Path,
        index_path: Path,
        on_update: Optional[Callable[[str], None]] = None,
        debounce_seconds: float = 1.0,
    ):
        """初始化文件处理器

        Args:
            project_root: 项目根目录
            index_path: 连续性索引文件路径
            on_update: 更新回调函数（可选）
            debounce_seconds: 防抖延迟（秒）
        """
        super().__init__()
        self.project_root = project_root
        self.index_path = index_path
        self.on_update = on_update
        self.debounce_seconds = debounce_seconds

        # 防抖机制：避免短时间内多次更新
        self._update_timer: Optional[threading.Timer] = None
        self._pending_files: set[str] = set()
        self._lock = threading.Lock()

    def on_modified(self, event: FileSystemEvent) -> None:
        """文件修改事件"""
        if event.is_directory:
            return
        self._handle_file_change(event.src_path, "modified")

    def on_created(self, event: FileSystemEvent) -> None:
        """文件创建事件"""
        if event.is_directory:
            return
        self._handle_file_change(event.src_path, "created")

    def on_deleted(self, event: FileSystemEvent) -> None:
        """文件删除事件"""
        if event.is_directory:
            return
        self._handle_file_change(event.src_path, "deleted")

    def _handle_file_change(self, file_path: str, event_type: str) -> None:
        """处理文件变更"""
        # 只处理 .md 文件
        if not file_path.endswith(".md"):
            return

        # 忽略临时文件和隐藏文件
        file_name = Path(file_path).name
        if file_name.startswith(".") or file_name.startswith("~"):
            return

        logger.info(f"检测到文件 {event_type}: {file_path}")

        with self._lock:
            self._pending_files.add(file_path)

            # 取消之前的定时器
            if self._update_timer is not None:
                self._update_timer.cancel()

            # 启动新的防抖定时器
            self._update_timer = threading.Timer(self.debounce_seconds, self._update_index)
            self._update_timer.daemon = True
            self._update_timer.start()

    def _update_index(self) -> None:
        """更新索引（防抖后执行）"""
        with self._lock:
            if not self._pending_files:
                return

            files = list(self._pending_files)
            self._pending_files.clear()

        logger.info(f"开始更新索引，涉及 {len(files)} 个文件")

        try:
            # 重新构建完整索引
            # TODO: 优化为增量更新
            start_time = time.time()
            build_continuity_index(self.project_root, output_path=self.index_path)
            elapsed = time.time() - start_time

            logger.info(f"✓ 索引更新完成，耗时 {elapsed:.2f}s")

            # 调用回调
            if self.on_update:
                for file_path in files:
                    self.on_update(file_path)

        except Exception as e:
            logger.error(f"✗ 索引更新失败: {e}", exc_info=True)


class FileWatcher:
    """文件监控管理器"""

    def __init__(
        self,
        project_root: Path,
        index_path: Path,
        watch_dirs: Optional[list[str]] = None,
        on_update: Optional[Callable[[str], None]] = None,
    ):
        """初始化文件监控器

        Args:
            project_root: 项目根目录
            index_path: 索引文件路径
            watch_dirs: 要监控的目录列表（默认：chapters, spec）
            on_update: 文件更新回调
        """
        self.project_root = Path(project_root)
        self.index_path = Path(index_path)
        self.watch_dirs = watch_dirs or ["chapters", "spec"]
        self.on_update = on_update

        self.observer: Optional[Any] = None  # Observer 类型标注问题
        self.handler = NovelFileHandler(
            project_root=self.project_root,
            index_path=self.index_path,
            on_update=on_update,
        )

    def start(self) -> None:
        """启动文件监控（阻塞模式）"""
        if self.observer is not None:
            logger.warning("文件监控已在运行")
            return

        self.observer = Observer()

        # 为每个目录添加监控
        for dir_name in self.watch_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                logger.warning(f"监控目录不存在，跳过: {dir_path}")
                continue

            self.observer.schedule(self.handler, str(dir_path), recursive=True)  # type: ignore[no-untyped-call]
            logger.info(f"开始监控目录: {dir_path}")

        self.observer.start()  # type: ignore[no-untyped-call]
        logger.info("✓ 文件监控已启动")

    def start_daemon(self) -> threading.Thread:
        """启动文件监控（后台线程）

        Returns:
            监控线程对象
        """
        if self.observer is not None and self.observer.is_alive():
            logger.warning("文件监控已在运行")
            return threading.current_thread()

        def run() -> None:
            try:
                self.observer = Observer()

                # 为每个目录添加监控
                for dir_name in self.watch_dirs:
                    dir_path = self.project_root / dir_name
                    if not dir_path.exists():
                        logger.warning(f"监控目录不存在，跳过: {dir_path}")
                        continue

                    self.observer.schedule(self.handler, str(dir_path), recursive=True)  # type: ignore[no-untyped-call]
                    logger.info(f"开始监控目录: {dir_path}")

                self.observer.start()  # type: ignore[no-untyped-call]
                logger.info("✓ 文件监控已启动（后台模式）")

                # 保持线程运行
                while self.observer and self.observer.is_alive():
                    time.sleep(1)
            except Exception as e:
                logger.error(f"文件监控线程异常: {e}", exc_info=True)

        thread = threading.Thread(target=run, name="FileWatcher", daemon=True)
        thread.start()

        # 等待 observer 启动
        time.sleep(0.1)

        return thread

    def stop(self) -> None:
        """停止文件监控"""
        if self.observer is None:
            return

        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join(timeout=5)

        self.observer = None
        logger.info("✓ 文件监控已停止")

    def is_running(self) -> bool:
        """检查监控是否运行中"""
        return self.observer is not None and self.observer.is_alive()


# 全局单例
_global_watcher: Optional[FileWatcher] = None


def get_file_watcher(
    project_root: Optional[Path] = None,
    index_path: Optional[Path] = None,
) -> FileWatcher:
    """获取全局文件监控器（单例模式）

    Args:
        project_root: 项目根目录（首次调用时必须提供）
        index_path: 索引路径（首次调用时必须提供）

    Returns:
        FileWatcher 实例
    """
    global _global_watcher

    if _global_watcher is None:
        if project_root is None or index_path is None:
            raise ValueError("首次调用必须提供 project_root 和 index_path")

        _global_watcher = FileWatcher(
            project_root=project_root,
            index_path=index_path,
        )

    return _global_watcher


def start_background_watcher(
    project_root: Path,
    index_path: Path,
) -> threading.Thread:
    """快捷启动后台文件监控

    Args:
        project_root: 项目根目录
        index_path: 索引路径

    Returns:
        监控线程对象
    """
    watcher = get_file_watcher(project_root, index_path)
    return watcher.start_daemon()


def stop_background_watcher() -> None:
    """快捷停止后台文件监控"""
    global _global_watcher
    if _global_watcher is not None:
        _global_watcher.stop()
