"""Alembic 环境：复用应用中的达梦数据库配置。

- URL 取自 app.core.config.settings（与数据库引擎使用相同来源）
- target_metadata 用 app.utils.database.Base.metadata（ORM 表定义）
- import app.utils.database 触发 dmSQLAlchemy 方言注册
"""
from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic.ddl import impl as alembic_impl
from sqlalchemy import engine_from_config, pool

from alembic import context

# 让 alembic 能找到 backend 包（alembic CLI 从 backend 目录运行时 cwd 已在路径上，
# 但程序内 command.upgrade 调用时不一定，这里显式补上，幂等）。
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.utils.database import Base  # noqa: E402  # 触发 dmSQLAlchemy 方言注册
import app.entity.models  # noqa: E402, F401 - 注册全部 ORM 表到 Base.metadata

# 覆盖 ini 里的 sqlalchemy.url，固定用 app 配置的一致来源。
# 注意：SQLAlchemy 2 的 str(url) 会把密码掩盖成 ***，必须显式 hide_password=False，
# 否则 alembic 回解析拿到的是 ***，连接报“用户名或密码错误”。
# 另外 configparser 会把 % 当插值标记，所以要把 URL 里的 % 再转义一层。
config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url.render_as_string(hide_password=False).replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata

# dmSQLAlchemy 注册了 SQLAlchemy 方言，但 Alembic 没有内置 "dm" 的 DDL 实现。
# 使用通用 DefaultImpl 即可让 Alembic 继续通过达梦 dialect 编译/执行 DDL。
alembic_impl._impls.setdefault("dm", alembic_impl.DefaultImpl)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
