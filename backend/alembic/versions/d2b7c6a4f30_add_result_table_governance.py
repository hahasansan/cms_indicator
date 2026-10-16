"""add result table governance metadata

Revision ID: d2b7c6a4f30
Revises: c28d9e7f5a10
Create Date: 2026-08-20 10:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision: str = "d2b7c6a4f30"
down_revision: Union[str, Sequence[str], None] = "c28d9e7f5a10"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"].upper() for column in inspect(op.get_bind()).get_columns(table)}


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if column.name.upper() not in _columns(table):
        op.add_column(table, column)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.has_table(bind, "result_tables"):
        _add_column_if_missing("result_tables", sa.Column("source_id", sa.String(64), nullable=True))
        _add_column_if_missing("result_tables", sa.Column("schema_name", sa.String(128), nullable=False, server_default=""))
        _add_column_if_missing("result_tables", sa.Column("dimension_capacity", sa.Integer(), nullable=False, server_default="20"))
        _add_column_if_missing("result_tables", sa.Column("physical_status", sa.String(32), nullable=False, server_default="unknown"))
        _add_column_if_missing("result_tables", sa.Column("last_checked_at", sa.DateTime(), nullable=True))
        _add_column_if_missing("result_tables", sa.Column("last_check_message", sa.Text(), nullable=False, server_default=""))

        source_id = bind.execute(text("SELECT id FROM data_sources WHERE id = 'ds_dm_system'")).scalar()
        if not source_id:
            row = bind.execute(text("SELECT id FROM data_sources ORDER BY created_at")).first()
            source_id = row[0] if row else None
        if source_id:
            bind.execute(text("UPDATE result_tables SET source_id = :source_id WHERE source_id IS NULL OR source_id = ''"), {"source_id": source_id})

    if not bind.dialect.has_table(bind, "result_table_change_logs"):
        op.create_table(
            "result_table_change_logs",
            sa.Column("id", sa.String(64), nullable=False),
            sa.Column("result_table_id", sa.String(64), nullable=False),
            sa.Column("table_name", sa.String(128), nullable=False),
            sa.Column("action", sa.String(32), nullable=False),
            sa.Column("operator", sa.String(64), nullable=False),
            sa.Column("detail_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("IX_RESULT_TABLE_LOG_TABLE", "result_table_change_logs", ["table_name", "created_at"])


def downgrade() -> None:
    raise RuntimeError("结果表治理元数据包含审计记录，不支持自动降级")
