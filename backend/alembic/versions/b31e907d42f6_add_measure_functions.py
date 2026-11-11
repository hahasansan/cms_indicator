"""Add reusable measure formula templates."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "b31e907d42f6"
down_revision: Union[str, Sequence[str], None] = "fa82d3b1c470"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not bind.dialect.has_table(bind, "measure_functions"):
        op.create_table(
            "measure_functions",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("formula", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.has_table(bind, "measure_functions"):
        op.drop_table("measure_functions")
