"""add dict tables: dict_categories / dict_sets / dict_items

码值管理三张表，业务编码唯一：
- dict_categories: category_code 唯一
- dict_sets: set_code 唯一，外键 dict_categories.id
- dict_items: (set_id, item_code) 唯一，外键 dict_sets.id

采用 op.create_table + sa.Column 方式（与 baseline 一致），
由 SQLAlchemy 达梦 dialect 处理大小写与 IDENTITY 语法。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "b9c1d4e6f701"
down_revision: Union[str, Sequence[str], None] = "a7f3e2c9b501"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return bind.dialect.has_table(bind, name)


def upgrade() -> None:
    # ===== dict_categories =====
    if not _has_table("dict_categories"):
        op.create_table(
            "dict_categories",
            sa.Column("id", sa.Integer(), sa.Identity(always=False, start=1), nullable=False),
            sa.Column("category_code", sa.String(length=64), nullable=False),
            sa.Column("category_name", sa.String(length=128), nullable=False),
            sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("category_code", name="uq_dict_category_code"),
        )

    # ===== dict_sets =====
    if not _has_table("dict_sets"):
        op.create_table(
            "dict_sets",
            sa.Column("id", sa.Integer(), sa.Identity(always=False, start=1), nullable=False),
            sa.Column("category_id", sa.Integer(), nullable=False),
            sa.Column("set_code", sa.String(length=64), nullable=False),
            sa.Column("set_name", sa.String(length=128), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="enabled"),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["category_id"], ["dict_categories.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("set_code", name="uq_dict_set_code"),
        )
        op.create_index("ix_dict_sets_category_id", "dict_sets", ["category_id"])

    # ===== dict_items =====
    if not _has_table("dict_items"):
        op.create_table(
            "dict_items",
            sa.Column("id", sa.Integer(), sa.Identity(always=False, start=1), nullable=False),
            sa.Column("set_id", sa.Integer(), nullable=False),
            sa.Column("item_code", sa.String(length=64), nullable=False),
            sa.Column("item_name", sa.String(length=128), nullable=False),
            sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="enabled"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["set_id"], ["dict_sets.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("set_id", "item_code", name="uq_dict_item_set_code"),
        )
        op.create_index("ix_dict_items_set_id", "dict_items", ["set_id"])


def downgrade() -> None:
    if _has_table("dict_items"):
        op.drop_table("dict_items")
    if _has_table("dict_sets"):
        op.drop_table("dict_sets")
    if _has_table("dict_categories"):
        op.drop_table("dict_categories")
