"""Tests for session persistence"""

import tempfile
from pathlib import Path

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver


class TestSessionPersistence:
    """测试会话持久化功能"""

    def test_sqlite_saver_context_manager(self) -> None:
        """测试SqliteSaver的with语句使用"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.sqlite"

            # 使用with语句创建checkpointer
            with SqliteSaver.from_conn_string(str(db_path)) as checkpointer:
                assert checkpointer is not None

                # 创建一个简单的checkpoint配置
                config: RunnableConfig = {
                    "configurable": {"thread_id": "test-1", "checkpoint_ns": ""}
                }

                # 验证checkpointer可以使用
                # Note: get()在没有数据时返回None，这是正常行为
                result = checkpointer.get(config)
                assert result is None  # 没有保存过，应该返回None

            # with块外，数据库文件应该已创建
            assert db_path.exists()

    def test_multiple_checkpointers(self) -> None:
        """测试多个独立的checkpointer实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db1 = Path(tmpdir) / "db1.sqlite"
            db2 = Path(tmpdir) / "db2.sqlite"

            # 创建两个独立的checkpointer
            with SqliteSaver.from_conn_string(str(db1)) as cp1:
                assert cp1 is not None

            with SqliteSaver.from_conn_string(str(db2)) as cp2:
                assert cp2 is not None

            # 两个数据库文件都应该被创建
            assert db1.exists()
            assert db2.exists()

    def test_checkpointer_lifecycle(self) -> None:
        """测试checkpointer的生命周期管理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "lifecycle.sqlite"

            # with语句应该正确管理资源
            with SqliteSaver.from_conn_string(str(db_path)) as checkpointer:
                # 在with块内，checkpointer可用
                config: RunnableConfig = {
                    "configurable": {"thread_id": "test", "checkpoint_ns": ""}
                }
                assert checkpointer.get(config) is None

            # with块结束后，数据库文件存在
            assert db_path.exists()
            assert db_path.stat().st_size > 0
