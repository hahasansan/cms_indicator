"""数据库迁移执行器：启动时把 schema 升级到 Alembic 最新（替代 create_all + 启动 ALTER）。

baseline 迁移是幂等的：全新库建全量表，历史库无痛跳过/补列。
"""
from __future__ import annotations

from pathlib import Path

from alembic import command, config

BACKEND_DIR = Path(__file__).resolve().parents[2]


def run_migrations() -> None:
    """程序内执行 ``alembic upgrade head``。"""
    cfg = config.Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")