"""智能缓存模块

提供多层缓存支持：
1. LLM 响应缓存（基于 LangChain InMemoryCache）
2. 图查询缓存（基于 diskcache）
3. 文件读取缓存（基于文件修改时间）
"""

import hashlib
import os
from pathlib import Path
from typing import Any, Optional

import diskcache  # type: ignore[import-untyped]
from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache

from .logging_config import get_logger

logger = get_logger(__name__)


class CacheManager:
    """缓存管理器"""

    def __init__(self, cache_dir: str = ".cache", ttl: int = 3600):
        """初始化缓存管理器

        Args:
            cache_dir: 缓存目录
            ttl: 默认 TTL（秒），默认 1 小时
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl

        # 图查询缓存
        self.graph_cache = diskcache.Cache(str(self.cache_dir / "graph"))

        # 文件缓存（内存缓存，key: path, value: (mtime, content)）
        self.file_cache: dict[str, tuple[float, str]] = {}

        # 统计
        self.stats = {"hits": 0, "misses": 0, "graph_hits": 0, "file_hits": 0}

        logger.info(f"缓存管理器初始化完成: {cache_dir}")

    def enable_llm_cache(self) -> None:
        """启用 LLM 响应缓存（内存缓存）"""
        set_llm_cache(InMemoryCache())
        logger.info("LLM 缓存已启用（内存模式）")

    def disable_llm_cache(self) -> None:
        """禁用 LLM 响应缓存"""
        set_llm_cache(None)
        logger.info("LLM 缓存已禁用")

    def cache_graph_query(self, query_key: str, result: Any, ttl: Optional[int] = None) -> None:
        """缓存图查询结果

        Args:
            query_key: 查询键（自动 hash）
            result: 查询结果
            ttl: 过期时间（秒），None 使用默认值
        """
        key = self._hash_key(query_key)
        expire_time = ttl if ttl is not None else self.ttl
        self.graph_cache.set(key, result, expire=expire_time)
        logger.debug(f"图查询缓存: {query_key[:50]}... (TTL: {expire_time}s)")

    def get_graph_query(self, query_key: str) -> Optional[Any]:
        """获取图查询缓存

        Args:
            query_key: 查询键

        Returns:
            缓存的结果，如果不存在返回 None
        """
        key = self._hash_key(query_key)
        result = self.graph_cache.get(key)
        if result is not None:
            self.stats["graph_hits"] += 1
            self.stats["hits"] += 1
            logger.debug(f"图查询缓存命中: {query_key[:50]}...")
        else:
            self.stats["misses"] += 1
        return result

    def cache_file_content(self, path: str, content: str) -> None:
        """缓存文件内容

        Args:
            path: 文件路径
            content: 文件内容
        """
        try:
            mtime = os.path.getmtime(path)
            self.file_cache[path] = (mtime, content)
            logger.debug(f"文件缓存: {path}")
        except OSError:
            pass

    def get_file_content(self, path: str) -> Optional[str]:
        """获取文件缓存

        如果文件已修改，自动失效缓存

        Args:
            path: 文件路径

        Returns:
            缓存的内容，如果不存在或已失效返回 None
        """
        if path not in self.file_cache:
            self.stats["misses"] += 1
            return None

        cached_mtime, cached_content = self.file_cache[path]

        try:
            current_mtime = os.path.getmtime(path)
            if current_mtime == cached_mtime:
                # 文件未修改，缓存有效
                self.stats["file_hits"] += 1
                self.stats["hits"] += 1
                logger.debug(f"文件缓存命中: {path}")
                return cached_content
            else:
                # 文件已修改，删除缓存
                del self.file_cache[path]
                self.stats["misses"] += 1
                logger.debug(f"文件缓存失效（已修改）: {path}")
                return None
        except OSError:
            # 文件不存在，删除缓存
            del self.file_cache[path]
            self.stats["misses"] += 1
            return None

    def clear(self) -> None:
        """清空所有缓存"""
        self.graph_cache.clear()
        self.file_cache.clear()
        self.stats = {"hits": 0, "misses": 0, "graph_hits": 0, "file_hits": 0}
        logger.info("所有缓存已清空")

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计信息

        Returns:
            包含命中率等统计信息的字典
        """
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total * 100 if total > 0 else 0

        return {
            "total_queries": total,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": hit_rate,
            "graph_hits": self.stats["graph_hits"],
            "file_hits": self.stats["file_hits"],
        }

    def _hash_key(self, key: str) -> str:
        """生成 hash key

        Args:
            key: 原始 key

        Returns:
            SHA256 hash
        """
        return hashlib.sha256(key.encode()).hexdigest()


# 全局缓存管理器实例
_cache_manager: Optional[CacheManager] = None


def get_cache_manager(cache_dir: str = ".cache") -> CacheManager:
    """获取全局缓存管理器实例

    Args:
        cache_dir: 缓存目录

    Returns:
        CacheManager 实例
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(cache_dir)
    return _cache_manager


def enable_cache(cache_dir: str = ".cache") -> CacheManager:
    """启用缓存

    Args:
        cache_dir: 缓存目录

    Returns:
        CacheManager 实例
    """
    manager = get_cache_manager(cache_dir)
    manager.enable_llm_cache()
    return manager


def disable_cache() -> None:
    """禁用缓存"""
    global _cache_manager
    if _cache_manager:
        _cache_manager.disable_llm_cache()
        _cache_manager = None
