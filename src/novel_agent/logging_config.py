"""Logging Configuration

配置项目的日志记录
"""

import logging
import os
import sys
import warnings
from pathlib import Path


def setup_logging(
    level: str = "INFO", log_file: str | None = None, console_output: bool = True
) -> None:
    """配置日志记录

    Args:
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        log_file: 日志文件路径（可选）
        console_output: 是否输出到控制台（交互模式下应设为 False）
    """
    # 如果禁用控制台输出，同时抑制所有警告和第三方库日志
    if not console_output:
        # 抑制 Python warnings
        warnings.filterwarnings("ignore")

        # 抑制 gRPC 日志（通过环境变量）
        os.environ["GRPC_VERBOSITY"] = "ERROR"
        os.environ["GRPC_TRACE"] = ""

        # 抑制 TensorFlow 日志（如果使用）
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

    # 转换日志级别
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # 配置日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # 配置handlers
    handlers: list[logging.Handler] = []

    # 只在非交互模式下输出到控制台
    if console_output:
        handlers.append(logging.StreamHandler(sys.stdout))

    if log_file:
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 添加文件handler
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        handlers.append(file_handler)
    else:
        # 如果没有指定日志文件且禁用控制台输出，使用默认日志文件
        if not console_output:
            default_log = Path("logs/novel-agent.log")
            default_log.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(default_log, encoding="utf-8")
            handlers.append(file_handler)

    # 配置root logger
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
        force=True,  # 覆盖已有配置
    )

    # 为novel_agent模块设置日志
    logger = logging.getLogger("novel_agent")
    logger.setLevel(numeric_level)

    # 降低第三方库的日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.ERROR)
    logging.getLogger("grpc").setLevel(logging.ERROR)
    logging.getLogger("absl").setLevel(logging.ERROR)

    # 如果禁用控制台输出，将所有第三方库设为 ERROR 级别
    if not console_output:
        for logger_name in [
            "httpx",
            "httpcore",
            "langchain",
            "google",
            "grpc",
            "absl",
            "urllib3",
            "asyncio",
        ]:
            logging.getLogger(logger_name).setLevel(logging.ERROR)
            logging.getLogger(logger_name).propagate = False


def get_logger(name: str) -> logging.Logger:
    """获取logger实例

    Args:
        name: logger名称（通常是__name__）

    Returns:
        Logger实例
    """
    return logging.getLogger(f"novel_agent.{name}")
