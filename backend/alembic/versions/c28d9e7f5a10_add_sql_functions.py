"""add sql functions

Revision ID: c28d9e7f5a10
Revises: a41e7c9b2d10
Create Date: 2026-08-19 16:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c28d9e7f5a10"
down_revision: Union[str, Sequence[str], None] = "a41e7c9b2d10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not bind.dialect.has_table(bind, "sql_functions"):
        op.create_table(
            "sql_functions",
            sa.Column("id", sa.String(64), nullable=False),
            sa.Column("code", sa.String(64), nullable=False),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("function_type", sa.String(16), nullable=False),
            sa.Column("category", sa.String(64), nullable=False),
            sa.Column("usage_scope", sa.Text(), nullable=False),
            sa.Column("render_mode", sa.String(16), nullable=False),
            sa.Column("template_sql", sa.Text(), nullable=False),
            sa.Column("args_json", sa.Text(), nullable=False),
            sa.Column("return_type", sa.String(32), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("example", sa.Text(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("editable", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code"),
        )


def downgrade() -> None:
    op.drop_table("sql_functions")
