"""Add operand meanings to measure formula templates."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "d4a1f7c3e205"
down_revision: Union[str, Sequence[str], None] = "b31e907d42f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not bind.dialect.has_table(bind, "measure_functions"):
        return
    columns = {column["name"] for column in inspect(bind).get_columns("measure_functions")}
    if "parameters" not in columns:
        op.add_column("measure_functions", sa.Column("parameters", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if not bind.dialect.has_table(bind, "measure_functions"):
        return
    columns = {column["name"] for column in inspect(bind).get_columns("measure_functions")}
    if "parameters" in columns:
        op.drop_column("measure_functions", "parameters")
