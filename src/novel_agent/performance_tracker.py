"""性能跟踪器

跟踪 API 调用、缓存命中率等性能指标
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PerformanceStats:
    """性能统计"""

    # API 调用统计
    llm_calls: int = 0
    tool_calls: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    # 时间统计
    total_time: float = 0.0
    llm_time: float = 0.0
    tool_time: float = 0.0

    # 工具调用详情
    tool_call_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def add_llm_call(self, duration: float = 0.0) -> None:
        """记录 LLM 调用"""
        self.llm_calls += 1
        self.llm_time += duration

    def add_tool_call(self, tool_name: str, duration: float = 0.0) -> None:
        """记录工具调用"""
        self.tool_calls += 1
        self.tool_time += duration
        self.tool_call_counts[tool_name] += 1

    def add_cache_hit(self) -> None:
        """记录缓存命中"""
        self.cache_hits += 1

    def add_cache_miss(self) -> None:
        """记录缓存未命中"""
        self.cache_misses += 1

    @property
    def cache_hit_rate(self) -> float:
        """缓存命中率"""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": f"{self.cache_hit_rate:.1%}",
            "total_time": f"{self.total_time:.2f}s",
            "llm_time": f"{self.llm_time:.2f}s",
            "tool_time": f"{self.tool_time:.2f}s",
            "tool_breakdown": dict(self.tool_call_counts),
        }

    def format_summary(self) -> str:
        """格式化摘要"""
        total_cache = self.cache_hits + self.cache_misses
        lines = [
            "📊 性能统计",
            f"  LLM 调用: {self.llm_calls} 次",
            f"  工具调用: {self.tool_calls} 次",
            f"  缓存命中率: {self.cache_hit_rate:.1%} ({self.cache_hits}/{total_cache})",
            f"  总耗时: {self.total_time:.2f}s",
        ]

        if self.tool_call_counts:
            lines.append("  工具使用:")
            for tool_name, count in sorted(
                self.tool_call_counts.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"    {tool_name}: {count} 次")

        return "\n".join(lines)


class PerformanceTracker:
    """性能跟踪器"""

    def __init__(self) -> None:
        self.stats = PerformanceStats()
        self._start_time: float | None = None

    def start(self) -> None:
        """开始跟踪"""
        self._start_time = time.time()

    def stop(self) -> None:
        """停止跟踪"""
        if self._start_time is not None:
            self.stats.total_time = time.time() - self._start_time
            self._start_time = None

    def record_llm_call(self, duration: float = 0.0) -> None:
        """记录 LLM 调用"""
        self.stats.add_llm_call(duration)

    def record_tool_call(self, tool_name: str, duration: float = 0.0) -> None:
        """记录工具调用"""
        self.stats.add_tool_call(tool_name, duration)

    def record_cache_hit(self) -> None:
        """记录缓存命中"""
        self.stats.add_cache_hit()

    def record_cache_miss(self) -> None:
        """记录缓存未命中"""
        self.stats.add_cache_miss()

    def get_stats(self) -> PerformanceStats:
        """获取统计信息"""
        return self.stats

    def reset(self) -> None:
        """重置统计"""
        self.stats = PerformanceStats()
        self._start_time = None


# 全局跟踪器实例
_global_tracker: PerformanceTracker | None = None


def get_tracker() -> PerformanceTracker:
    """获取全局跟踪器"""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = PerformanceTracker()
    return _global_tracker


def reset_tracker() -> None:
    """重置全局跟踪器"""
    global _global_tracker
    _global_tracker = PerformanceTracker()


__all__ = ["PerformanceStats", "PerformanceTracker", "get_tracker", "reset_tracker"]
