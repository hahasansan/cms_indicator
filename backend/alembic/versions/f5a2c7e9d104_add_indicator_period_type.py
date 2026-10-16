"""add indicator.period_type field"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision: str = "f5a2c7e9d104"
down_revision: Union[str, Sequence[str], None] = "e3a9d5c8b20"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"].upper() for column in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    """给 indicators 表加 PERIOD_TYPE 字段（point / period），存量数据默认 point。

    达梦大小写敏感：
    - 表名用无引号（达梦自动转大写 INDICATORS，与建表一致）
    - 列名用大写 + 带引号
    """
    bind = op.get_bind()
    if not bind.dialect.has_table(bind, "indicators"):
        return
    present = _columns("indicators")
    if "PERIOD_TYPE" not in present:
        bind.execute(text('ALTER TABLE indicators ADD "PERIOD_TYPE" VARCHAR(16)'))
    # 存量数据填默认值（point）
    bind.execute(text('UPDATE indicators SET "PERIOD_TYPE" = \'point\' WHERE "PERIOD_TYPE" IS NULL OR "PERIOD_TYPE" = \'\''))


def downgrade() -> None:
    """删除 indicators.PERIOD_TYPE 字段。"""
    bind = op.get_bind()
    if not bind.dialect.has_table(bind, "indicators"):
        return
    present = _columns("indicators")
    if "PERIOD_TYPE" in present:
        bind.execute(text('ALTER TABLE indicators DROP COLUMN "PERIOD_TYPE"'))


