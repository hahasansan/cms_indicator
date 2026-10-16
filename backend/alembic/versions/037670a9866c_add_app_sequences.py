"""add app_sequences

Revision ID: 037670a9866c
Revises: 4b4f10e2965d
Create Date: 2026-08-17 22:16:00.090062

内容：新增计数表 app_sequences，用于指标编码(INDxxxxx)生成，替代启动时扫全表取 max+1。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '037670a9866c'
down_revision: Union[str, Sequence[str], None] = '4b4f10e2965d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if not bind.dialect.has_table(bind, "app_sequences"):
        op.create_table(
            "app_sequences",
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("next_value", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("name"),
        )
    # 已存在的指标以当前最大编码续号，避免新编码撞号
    row = bind.execute(sa.text("SELECT MAX(CAST(SUBSTR(code, 4) AS INTEGER)) AS m FROM indicators WHERE code LIKE 'IND%'")).first()
    current = int(row[0]) if row and row[0] is not None else 0
    has = bind.execute(sa.text("SELECT 1 FROM app_sequences WHERE name = 'indicator_code'")).first()
    if not has:
        bind.execute(
            sa.text("INSERT INTO app_sequences (name, next_value) VALUES ('indicator_code', :v)"),
            {"v": current + 1},  # 下一个待用的编码号
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("app_sequences")