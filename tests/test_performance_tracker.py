"""性能跟踪器测试"""

import time

import pytest

from novel_agent.performance_tracker import (
    PerformanceStats,
    PerformanceTracker,
    get_tracker,
    reset_tracker,
)


class TestPerformanceStats:
    """测试性能统计"""

    def test_initial_stats(self) -> None:
        """测试初始统计

        验收标准：
        - 所有计数器初始化为 0
        """
        stats = PerformanceStats()

        assert stats.llm_calls == 0
        assert stats.tool_calls == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
        assert stats.total_time == 0.0

    def test_add_llm_call(self) -> None:
        """测试记录 LLM 调用

        验收标准：
        - LLM 调用计数增加
        - 时间累加
        """
        stats = PerformanceStats()

        stats.add_llm_call(0.5)
        stats.add_llm_call(0.3)

        assert stats.llm_calls == 2
        assert stats.llm_time == 0.8

    def test_add_tool_call(self) -> None:
        """测试记录工具调用

        验收标准：
        - 工具调用计数增加
        - 工具名称记录
        """
        stats = PerformanceStats()

        stats.add_tool_call("read_file", 0.1)
        stats.add_tool_call("write_chapter", 0.2)
        stats.add_tool_call("read_file", 0.15)

        assert stats.tool_calls == 3
        assert stats.tool_time == pytest.approx(0.45)
        assert stats.tool_call_counts["read_file"] == 2
        assert stats.tool_call_counts["write_chapter"] == 1

    def test_cache_hit_rate(self) -> None:
        """测试缓存命中率计算

        验收标准：
        - 正确计算百分比
        - 空集合返回 0.0
        """
        stats = PerformanceStats()

        # 空集合
        assert stats.cache_hit_rate == 0.0

        # 部分命中
        stats.add_cache_hit()
        stats.add_cache_hit()
        stats.add_cache_miss()

        assert stats.cache_hit_rate == pytest.approx(0.667, abs=0.01)

        # 全部命中
        stats.add_cache_hit()
        assert stats.cache_hit_rate == 0.75

    def test_to_dict(self) -> None:
        """测试转换为字典

        验收标准：
        - 包含所有关键字段
        - 格式化正确
        """
        stats = PerformanceStats()
        stats.add_llm_call(1.0)
        stats.add_tool_call("read_file", 0.5)
        stats.add_cache_hit()
        stats.total_time = 2.0

        result = stats.to_dict()

        assert result["llm_calls"] == 1
        assert result["tool_calls"] == 1
        assert "100.0%" in result["cache_hit_rate"]  # 1/(1+0) = 100%
        assert "2.00s" in result["total_time"]
        assert result["tool_breakdown"]["read_file"] == 1

    def test_format_summary(self) -> None:
        """测试格式化摘要

        验收标准：
        - 返回可读字符串
        - 包含关键信息
        """
        stats = PerformanceStats()
        stats.add_llm_call(1.0)
        stats.add_tool_call("read_file", 0.5)
        stats.add_cache_hit()
        stats.add_cache_miss()
        stats.total_time = 2.0

        summary = stats.format_summary()

        assert "LLM 调用: 1 次" in summary
        assert "工具调用: 1 次" in summary
        assert "缓存命中率: 50.0%" in summary
        assert "总耗时: 2.00s" in summary
        assert "read_file: 1 次" in summary


class TestPerformanceTracker:
    """测试性能跟踪器"""

    def test_initial_tracker(self) -> None:
        """测试初始跟踪器

        验收标准：
        - 统计为空
        """
        tracker = PerformanceTracker()

        stats = tracker.get_stats()
        assert stats.llm_calls == 0
        assert stats.tool_calls == 0

    def test_start_stop_tracking(self) -> None:
        """测试开始/停止跟踪

        验收标准：
        - 记录总耗时
        """
        tracker = PerformanceTracker()
        tracker.start()

        time.sleep(0.1)

        tracker.stop()

        assert tracker.get_stats().total_time >= 0.1

    def test_record_operations(self) -> None:
        """测试记录操作

        验收标准：
        - 正确记录各种操作
        """
        tracker = PerformanceTracker()

        tracker.record_llm_call(0.5)
        tracker.record_tool_call("read_file", 0.1)
        tracker.record_cache_hit()
        tracker.record_cache_miss()

        stats = tracker.get_stats()
        assert stats.llm_calls == 1
        assert stats.tool_calls == 1
        assert stats.cache_hits == 1
        assert stats.cache_misses == 1

    def test_reset_tracker(self) -> None:
        """测试重置跟踪器

        验收标准：
        - 清空所有统计
        """
        tracker = PerformanceTracker()

        tracker.record_llm_call()
        tracker.record_tool_call("test")

        tracker.reset()

        stats = tracker.get_stats()
        assert stats.llm_calls == 0
        assert stats.tool_calls == 0


class TestGlobalTracker:
    """测试全局跟踪器"""

    def test_get_global_tracker(self) -> None:
        """测试获取全局跟踪器

        验收标准：
        - 返回同一个实例
        """
        tracker1 = get_tracker()
        tracker2 = get_tracker()

        assert tracker1 is tracker2

    def test_reset_global_tracker(self) -> None:
        """测试重置全局跟踪器

        验收标准：
        - 创建新实例
        """
        tracker1 = get_tracker()
        tracker1.record_llm_call()

        reset_tracker()

        tracker2 = get_tracker()
        assert tracker2.get_stats().llm_calls == 0
