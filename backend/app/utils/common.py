"""通用工具函数。"""

from datetime import datetime
from secrets import token_hex


def new_id(prefix: str) -> str:
    """前缀 + 时间戳 + 随机后缀（避免并发微秒级撞号）。"""
    return f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}{token_hex(3)}"