"""允许 job_runs.single_date 为空。

时段类指标没有单日业务日期，single_date 只对余额类有意义。达梦把空字符串当作
NULL，因此之前写入 ``""`` 会触发非空约束。本次迁移去掉该列的非空约束，改由
business_start_date / business_end_date 记录区间。

达梦原生 ALTER 语法：``ALTER TABLE t MODIFY c NULL``。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name in {"dm", "dameng"}:
        try:
            bind.execute(sa.text("ALTER TABLE job_runs MODIFY single_date NULL"))
        except Exception as exc:
            msg = str(exc)
            if "不存在" in msg or "已为" in msg or "already null" in msg.lower():
                return
            raise
    else:
        op.alter_column("job_runs", "single_date", nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    # 回填时段类数据的空值，避免恢复非空约束失败
    bind.execute(
        sa.text(
            "UPDATE job_runs SET single_date = business_start_date "
            "WHERE single_date IS NULL AND business_start_date IS NOT NULL"
        )
    )
    if bind.dialect.name in {"dm", "dameng"}:
        bind.execute(sa.text("ALTER TABLE job_runs MODIFY single_date NOT NULL"))
    else:
        op.alter_column("job_runs", "single_date", nullable=False)
