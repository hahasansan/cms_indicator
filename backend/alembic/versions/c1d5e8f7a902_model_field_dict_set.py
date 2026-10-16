"""model_field: replace code_values with dict_set_id

- 删除 model_fields.code_values（存量数据为空，无需迁移）
- 新增 model_fields.dict_set_id INT NULL，外键 dict_sets.id
- 新增索引 ix_model_fields_dict_set_id

采用 op.add_column / op.drop_column（与增量迁移一致），
由 SQLAlchemy 达梦 dialect 处理大小写。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "c1d5e8f7a902"
down_revision: Union[str, Sequence[str], None] = "b9c1d4e6f701"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    bind = op.get_bind()
    if not bind.dialect.has_table(bind, table):
        return set()
    return {c["name"].lower() for c in inspect(bind).get_columns(table)}


def upgrade() -> None:
    cols = _columns("model_fields")
    # 1. 新增 dict_set_id 列
    if "dict_set_id" not in cols:
        op.add_column(
            "model_fields",
            sa.Column("dict_set_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "fk_model_fields_dict_set",
            "model_fields",
            "dict_sets",
            ["dict_set_id"],
            ["id"],
        )
        op.create_index("ix_model_fields_dict_set_id", "model_fields", ["dict_set_id"])

    # 2. 删除 code_values 列（存量数据为空，直接删）
    if "code_values" in cols:
        op.drop_column("model_fields", "code_values")


def downgrade() -> None:
    cols = _columns("model_fields")
    # 回退：先恢复 code_values，再删 dict_set_id
    if "code_values" not in cols:
        op.add_column(
            "model_fields",
            sa.Column("code_values", sa.Text(), nullable=True),
        )
    if "dict_set_id" in cols:
        op.drop_index("ix_model_fields_dict_set_id", table_name="model_fields")
        op.drop_constraint("fk_model_fields_dict_set", "model_fields", type_="foreignkey")
        op.drop_column("model_fields", "dict_set_id")
