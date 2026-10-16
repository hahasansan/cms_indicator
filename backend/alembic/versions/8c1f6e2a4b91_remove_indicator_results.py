"""remove legacy indicator_results detail table"""
from typing import Sequence, Union

from alembic import op


revision: str = "8c1f6e2a4b91"
down_revision: Union[str, Sequence[str], None] = "037670a9866c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.has_table(bind, "indicator_results"):
        op.drop_table("indicator_results")


def downgrade() -> None:
    raise RuntimeError("indicator_results 已删除，不能自动恢复历史明细数据")