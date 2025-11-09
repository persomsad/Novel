"""智能错误处理和友好提示

提供更好的错误提示和自动恢复机制
"""

import difflib
from pathlib import Path
from typing import Any


class FriendlyError(Exception):
    """友好的错误基类"""

    def __init__(self, message: str, suggestions: list[str] | None = None):
        super().__init__(message)
        self.message = message
        self.suggestions = suggestions or []

    def format_message(self) -> str:
        """格式化错误消息"""
        lines = [f"❌ {self.message}"]

        if self.suggestions:
            lines.append("\n💡 建议：")
            for suggestion in self.suggestions:
                lines.append(f"  - {suggestion}")

        return "\n".join(lines)


class FileNotFoundError_(FriendlyError):  # noqa: N801, N818
    """文件不存在错误（增强版）"""

    def __init__(self, path: str, search_dir: str = "."):
        # 查找相似文件
        similar_files = find_similar_files(path, search_dir, limit=3)

        suggestions = []
        if similar_files:
            suggestions.append("是否要查找相似文件？")
            for file in similar_files:
                suggestions.append(f"  找到: {file}")

        # 如果路径包含目录，检查目录是否存在
        file_path = Path(path)
        if not file_path.parent.exists():
            suggestions.append(f"目录不存在: {file_path.parent}")
            suggestions.append(f"创建目录: mkdir -p {file_path.parent}")
        else:
            suggestions.append(f"创建新文件: novel-agent write {path}")

        super().__init__(f"文件不存在: {path}", suggestions)


class APIKeyError(FriendlyError):
    """API Key 错误"""

    def __init__(self) -> None:
        suggestions = [
            "设置环境变量: export GOOGLE_API_KEY=your-api-key",
            "或在命令中指定: novel-agent chat --api-key YOUR_KEY",
            "获取 API Key: https://makersuite.google.com/app/apikey",
        ]
        super().__init__("未设置 Gemini API Key", suggestions)


class FormatError(FriendlyError):
    """格式错误"""

    def __init__(self, message: str, expected_format: str, example: str | None = None):
        suggestions = [f"期望格式: {expected_format}"]
        if example:
            suggestions.append(f"示例: {example}")

        super().__init__(message, suggestions)


class NetworkError(FriendlyError):
    """网络错误"""

    def __init__(self, message: str, retry_count: int = 0):
        suggestions = []
        if retry_count > 0:
            suggestions.append(f"已重试 {retry_count} 次")
        suggestions.extend(
            [
                "检查网络连接",
                "检查防火墙/代理设置",
                "稍后重试",
            ]
        )

        super().__init__(message, suggestions)


class TimeoutError_(FriendlyError):  # noqa: N801, N818
    """超时错误"""

    def __init__(self, message: str, timeout: int):
        suggestions = [
            f"当前超时设置: {timeout}s",
            "增加超时时间: --timeout 120",
            "或简化请求内容",
        ]

        super().__init__(message, suggestions)


def find_similar_files(target: str, search_dir: str = ".", limit: int = 3) -> list[str]:
    """查找相似文件

    Args:
        target: 目标文件路径
        search_dir: 搜索目录
        limit: 返回数量限制

    Returns:
        相似文件路径列表
    """
    target_path = Path(target)
    target_name = target_path.name

    search_path = Path(search_dir)
    if not search_path.exists():
        return []

    # 收集所有文件
    all_files: list[str] = []
    try:
        for file_path in search_path.rglob("*"):
            if file_path.is_file():
                all_files.append(str(file_path))
    except PermissionError:
        pass

    if not all_files:
        return []

    # 计算相似度
    similarities: list[tuple[str, float]] = []
    for file_str in all_files:
        file_name = Path(file_str).name
        ratio = difflib.SequenceMatcher(None, target_name, file_name).ratio()
        similarities.append((file_str, ratio))

    # 按相似度排序
    similarities.sort(key=lambda x: x[1], reverse=True)

    # 返回最相似的文件
    return [file_str for file_str, ratio in similarities[:limit] if ratio > 0.5]


def suggest_command(error_type: str, context: dict[str, Any]) -> list[str]:
    """根据错误类型建议命令

    Args:
        error_type: 错误类型
        context: 上下文信息

    Returns:
        命令建议列表
    """
    suggestions = []

    if error_type == "file_not_found":
        file_path = context.get("path", "")
        suggestions.append(f"创建文件: novel-agent write {file_path}")

    elif error_type == "api_key_missing":
        suggestions.extend(
            [
                "设置 API Key: export GOOGLE_API_KEY=your-key",
                "获取 API Key: https://makersuite.google.com/app/apikey",
            ]
        )

    elif error_type == "network_error":
        suggestions.extend(
            [
                "检查网络连接: ping google.com",
                "检查代理设置: echo $HTTP_PROXY",
            ]
        )

    return suggestions


def retry_with_backoff(func: Any, max_retries: int = 3, initial_delay: float = 1.0) -> Any:
    """带退避的重试机制

    Args:
        func: 要执行的函数
        max_retries: 最大重试次数
        initial_delay: 初始延迟（秒）

    Returns:
        函数执行结果

    Raises:
        NetworkError: 重试失败后抛出
    """
    import time

    delay = initial_delay

    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                # 最后一次重试失败
                raise NetworkError(f"操作失败: {str(e)}", retry_count=attempt + 1)

            # 等待后重试
            time.sleep(delay)
            delay *= 2  # 指数退避


__all__ = [
    "FriendlyError",
    "FileNotFoundError_",
    "APIKeyError",
    "FormatError",
    "NetworkError",
    "TimeoutError_",
    "find_similar_files",
    "suggest_command",
    "retry_with_backoff",
]
