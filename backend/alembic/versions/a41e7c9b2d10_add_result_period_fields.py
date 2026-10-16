"""add result period fields"""
from typing import Sequence, Union
import re

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision: str = "a41e7c9b2d10"
down_revision: Union[str, Sequence[str], None] = "8c1f6e2a4b91"
branch_labels = None
depends_on = None

_IDENT_RE = re.compile(r"^[A-Za-z0-9_一-鿿]+$")


def _quote(name: str) -> str:
    if not _IDENT_RE.fullmatch(name):
        raise RuntimeError(f"非法结果表名：{name}")
    return '"' + name.replace('"', '""') + '"'


def _columns(table: str) -> set[str]:
    return {column["name"].upper() for column in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.has_table(bind, "job_runs"):
        present = _columns("job_runs")
        if "BUSINESS_START_DATE" not in present:
            op.add_column("job_runs", sa.Column("business_start_date", sa.String(16), nullable=True))
        if "BUSINESS_END_DATE" not in present:
            op.add_column("job_runs", sa.Column("business_end_date", sa.String(16), nullable=True))

    if not bind.dialect.has_table(bind, "result_tables"):
        return
    for (table_name,) in bind.execute(text("SELECT table_name FROM result_tables")).all():
        if not bind.dialect.has_table(bind, table_name):
            continue
        present = _columns(table_name)
        qtable = _quote(table_name)
        for name in ("RESULT_KIND", "PERIOD_TYPE", "PERIOD_START", "PERIOD_END"):
            if name not in present:
                bind.execute(text(f'ALTER TABLE {qtable} ADD "{name}" VARCHAR(16)'))
        bind.execute(text(f'UPDATE {qtable} SET "PERIOD_TYPE" = \'point\' WHERE "PERIOD_TYPE" IS NULL'))
        bind.execute(text(f'UPDATE {qtable} SET "RESULT_KIND" = CASE WHEN "PERIOD_TYPE" = \'period\' THEN \'summary\' ELSE \'detail\' END WHERE "RESULT_KIND" IS NULL OR "RESULT_KIND" = \'\''))
        bind.execute(text(f'UPDATE {qtable} SET "PERIOD_START" = "DATA_DATE" WHERE "PERIOD_START" IS NULL'))
        bind.execute(text(f'UPDATE {qtable} SET "PERIOD_END" = "DATA_DATE" WHERE "PERIOD_END" IS NULL'))
        index_prefix = re.sub(r"[^A-Za-z0-9_]", "_", table_name)[:80]
        bind.execute(text(f'CREATE INDEX IF NOT EXISTS "IX_{index_prefix}_CODE_DATE" ON {qtable} ("INDICATOR_CODE", "DATA_DATE")'))
        bind.execute(text(f'CREATE INDEX IF NOT EXISTS "IX_{index_prefix}_CODE_PERIOD" ON {qtable} ("INDICATOR_CODE", "PERIOD_TYPE", "PERIOD_START", "PERIOD_END")'))


def downgrade() -> None:
    raise RuntimeError("结果期间字段包含历史数据，不支持自动降级")