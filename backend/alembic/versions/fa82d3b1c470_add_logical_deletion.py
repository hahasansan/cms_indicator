"""Add logical deletion timestamps to models and indicators."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "fa82d3b1c470"
down_revision: Union[str, Sequence[str], None] = "eab417c9d260"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"].lower() for column in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    for table in ("data_models", "indicators"):
        if "deleted_at" not in _columns(table):
            op.add_column(table, sa.Column("deleted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    for table in ("indicators", "data_models"):
        if "deleted_at" in _columns(table):
            op.drop_column(table, "deleted_at")
