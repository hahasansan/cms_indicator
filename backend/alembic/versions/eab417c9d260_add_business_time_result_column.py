"""Add business time value to unified indicator results."""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect, text


revision: str = "eab417c9d260"
down_revision: Union[str, Sequence[str], None] = "c1d5e8f7a902"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {
        column["name"].upper()
        for column in inspect(op.get_bind()).get_columns(table)
    }


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.has_table(bind, "T_IND_RESULT") and "BUSINESS_TIME" not in _columns("T_IND_RESULT"):
        bind.execute(text('ALTER TABLE "T_IND_RESULT" ADD "BUSINESS_TIME" VARCHAR(255)'))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.has_table(bind, "T_IND_RESULT") and "BUSINESS_TIME" in _columns("T_IND_RESULT"):
        bind.execute(text('ALTER TABLE "T_IND_RESULT" DROP COLUMN "BUSINESS_TIME"'))
