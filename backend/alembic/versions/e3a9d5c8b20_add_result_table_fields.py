"""add result table custom fields

Revision ID: e3a9d5c8b20
Revises: d2b7c6a4f30
Create Date: 2026-08-20 11:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3a9d5c8b20"
down_revision: Union[str, Sequence[str], None] = "d2b7c6a4f30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not bind.dialect.has_table(bind, "result_table_fields"):
        op.create_table(
            "result_table_fields",
            sa.Column("id", sa.String(64), nullable=False),
            sa.Column("result_table_id", sa.String(64), nullable=False),
            sa.Column("field_name", sa.String(128), nullable=False),
            sa.Column("data_type", sa.String(32), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("IX_RESULT_TABLE_FIELDS_TABLE", "result_table_fields", ["result_table_id", "sort_order"])
        op.create_index("UX_RESULT_TABLE_FIELDS_NAME", "result_table_fields", ["result_table_id", "field_name"], unique=True)


def downgrade() -> None:
    raise RuntimeError("结果表字段元数据可能承载人工维护口径，不支持自动降级")
