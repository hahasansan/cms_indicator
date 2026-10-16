"""统一日志配置。

供 main 启动时调用一次；service 层用 ``logging.getLogger("indicator_system")`` 取子 logger。
"""
from __future__ import annotations

import logging
import sys

LOGGER_NAME = "indicator_system"


def setup_logging(level: int = logging.INFO) -> None:
    """幂等地配置根日志：只挂一个 StreamHandler，避免重复。"""
    root = logging.getLogger(LOGGER_NAME)
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    """取命名空间 logger（子 logger，自动继承 handler 与格式）。"""
    return logging.getLogger(f"{LOGGER_NAME}.{name}")
