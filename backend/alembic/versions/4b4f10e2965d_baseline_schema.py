"""baseline schema

Revision ID: 4b4f10e2965d
Revises:
Create Date: 2026-08-17 21:44:52.443190

说明：首个基线迁移。写成幂等（表存在则跳过、列缺失则补），
既能在全新库建全量 schema，也能在历史库（已由早前 create_all+启动 ALTER 建成）上无痛升级。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '4b4f10e2965d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return bind.dialect.has_table(bind, name)


def _missing_columns(table: str) -> list[str]:
    bind = op.get_bind()
    if not bind.dialect.has_table(bind, table):
        return []
    existing = {c["name"].lower() for c in inspect(bind).get_columns(table)}
    return existing


MISSING_COLUMNS: dict[str, list[tuple[str, sa.Column]]] = {
    "indicators": [
        ("parent_id", sa.Column("parent_id", sa.String(64), nullable=True)),
    ],
    "data_models": [
        ("source_type", sa.Column("source_type", sa.String(32), nullable=False, server_default="table")),
        ("source_sql", sa.Column("source_sql", sa.Text(), nullable=True)),
        ("source_ref", sa.Column("source_ref", sa.String(64), nullable=True)),
        ("source_template", sa.Column("source_template", sa.Text(), nullable=True)),
        ("biz_date_type", sa.Column("biz_date_type", sa.String(16), nullable=True)),
        ("biz_date_field", sa.Column("biz_date_field", sa.String(64), nullable=True)),
        ("biz_date_start_param", sa.Column("biz_date_start_param", sa.String(64), nullable=True)),
        ("biz_date_end_param", sa.Column("biz_date_end_param", sa.String(64), nullable=True)),
    ],
    "schedules": [
        ("date_option", sa.Column("date_option", sa.Text(), nullable=True)),
        ("scope", sa.Column("scope", sa.String(16), nullable=False, server_default="selected")),
        ("category_id", sa.Column("category_id", sa.String(64), nullable=True)),
    ],
}


def upgrade() -> None:
    """Upgrade schema."""
    def create_if_missing(name: str, builder) -> None:
        if not _has_table(name):
            builder()

    create_if_missing("data_models", lambda: op.create_table('data_models',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('module', sa.String(length=64), nullable=False),
        sa.Column('table_name', sa.String(length=128), nullable=False),
        sa.Column('owner', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('source_type', sa.String(length=32), nullable=False, server_default="table"),
        sa.Column('source_sql', sa.Text(), nullable=True),
        sa.Column('source_ref', sa.String(length=64), nullable=True),
        sa.Column('source_template', sa.Text(), nullable=True),
        sa.Column('biz_date_type', sa.String(length=16), nullable=True),
        sa.Column('biz_date_field', sa.String(length=64), nullable=True),
        sa.Column('biz_date_start_param', sa.String(length=64), nullable=True),
        sa.Column('biz_date_end_param', sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    ))

    create_if_missing("indicator_categories", lambda: op.create_table('indicator_categories',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('parent_id', sa.String(length=64), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    ))

    create_if_missing("indicator_results", lambda: op.create_table('indicator_results',
        sa.Column('id', sa.Integer(), sa.Identity(always=False, start=1), nullable=False),
        sa.Column('indicator_code', sa.String(length=64), nullable=False),
        sa.Column('data_date', sa.String(length=16), nullable=False),
        sa.Column('dim_json', sa.Text(), nullable=False),
        sa.Column('metric_name', sa.String(length=128), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=True),
        sa.Column('run_id', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    ))

    create_if_missing("job_runs", lambda: op.create_table('job_runs',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('indicator_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('run_date', sa.String(length=16), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=False),
        sa.Column('sql_text', sa.Text(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    ))

    create_if_missing("result_tables", lambda: op.create_table('result_tables',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('table_name', sa.String(length=128), nullable=False),
        sa.Column('comment', sa.String(length=255), nullable=False),
        sa.Column('frequency', sa.String(length=32), nullable=False),
        sa.Column('bound', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('table_name')
    ))

    create_if_missing("indicators", lambda: op.create_table('indicators',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('model_id', sa.String(length=64), nullable=True),
        sa.Column('parent_id', sa.String(length=64), nullable=True),
        sa.Column('category_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('favorite', sa.Boolean(), nullable=False),
        sa.Column('config_json', sa.Text(), nullable=False),
        sa.Column('sql_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['model_id'], ['data_models.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    ))

    create_if_missing("model_fields", lambda: op.create_table('model_fields',
        sa.Column('id', sa.Integer(), sa.Identity(always=False, start=1), nullable=False),
        sa.Column('model_id', sa.String(length=64), nullable=False),
        sa.Column('field_name', sa.String(length=128), nullable=False),
        sa.Column('alias', sa.String(length=128), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False),
        sa.Column('data_type', sa.String(length=32), nullable=False),
        sa.Column('unit', sa.String(length=32), nullable=False),
        sa.Column('is_date', sa.Boolean(), nullable=False),
        sa.Column('is_org', sa.Boolean(), nullable=False),
        sa.Column('filterable', sa.Boolean(), nullable=False),
        sa.Column('code_values', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['model_id'], ['data_models.id'], ),
        sa.PrimaryKeyConstraint('id')
    ))

    create_if_missing("indicator_versions", lambda: op.create_table('indicator_versions',
        sa.Column('id', sa.Integer(), sa.Identity(always=False, start=1), nullable=False),
        sa.Column('indicator_id', sa.String(length=64), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('config_json', sa.Text(), nullable=False),
        sa.Column('sql_text', sa.Text(), nullable=False),
        sa.Column('saved_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['indicator_id'], ['indicators.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    ))

    create_if_missing("schedules", lambda: op.create_table('schedules',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('indicator_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('frequency', sa.String(length=32), nullable=False),
        sa.Column('run_time', sa.String(length=16), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('date_option', sa.Text(), nullable=True),
        sa.Column('scope', sa.String(length=16), nullable=False, server_default="selected"),
        sa.Column('category_id', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['indicator_id'], ['indicators.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    ))

    # 历史库兜底补列（早前启动时 ALTER 补过，理论上都在；幂等保险）
    for table, columns in MISSING_COLUMNS.items():
        if not _has_table(table):
            continue
        present = {c["name"].lower() for c in inspect(op.get_bind()).get_columns(table)}
        for name, col in columns:
            if name.lower() not in present:
                op.add_column(table, col)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('schedules')
    op.drop_table('indicator_versions')
    op.drop_table('model_fields')
    op.drop_table('indicators')
    op.drop_table('result_tables')
    op.drop_table('job_runs')
    op.drop_table('indicator_results')
    op.drop_table('indicator_categories')
    op.drop_table('data_models')