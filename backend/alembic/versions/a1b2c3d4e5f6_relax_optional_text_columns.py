"""Make optional text columns nullable for DM compatibility.

达梦数据库空字符串会被当作 NULL，非空字段上的 ``default=""`` 写法会导致保存时
触发违反列非空约束。本次迁移把所有业务上可选的 description / remark / unit /
message / example 列改成 nullable=True，SQLAlchemy ORM 注解同步更新。

达梦 ALTER 语法注：dmPython/dmSQLAlchemy 不支持 ``ALTER COLUMN xxx DROP NOT NULL``
（这是 PostgreSQL/MSSQL 语法）。达梦原生语法为 ``ALTER TABLE t MODIFY [COLUMN] c NULL``
或 ``ALTER TABLE t ALTER COLUMN c NULL``，本脚本直接下发达梦原生 SQL 绕开 Alembic 的
dialect 差异。

此外，达梦里 ``col = ''`` 等价于 ``col IS NULL``，所以原本想先把空串 UPDATE 成 NULL
这一步实际上在达梦里根本命不中任何行——直接 ALTER 即可，达梦允许把已有数据的列
改成允许 NULL。

覆盖列：
- data_models.description
- model_fields.unit
- job_runs.message
- measure_functions.description
- sql_functions.description, example
- result_table_fields.description
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "d4a1f7c3e205"
branch_labels = None
depends_on = None


COLUMNS_TO_RELAX: list[tuple[str, str]] = [
    ("data_models",          "description"),
    ("model_fields",         "unit"),
    ("job_runs",             "message"),
    ("measure_functions",      "description"),
    ("sql_functions",          "description"),
    ("sql_functions",          "example"),
    ("result_table_fields",   "description"),
]


def _dm_alter_column_null(bind, table_name: str, column_name: str) -> None:
    """达梦原生 ALTER 语法：ALTER TABLE t MODIFY c NULL"""
    sql = f"ALTER TABLE {table_name} MODIFY {column_name} NULL"
    try:
        bind.execute(sa.text(sql))
    except Exception as exc:
        # 列已经是 NULL 时达梦会报错，忽略即可
        msg = str(exc)
        if "不存在" in msg or "已为" in msg or "already null" in msg.lower():
            return
        raise


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    for table_name, column_name in COLUMNS_TO_RELAX:
        if not bind.dialect.has_table(bind, table_name):
            continue
        present = {c["name"].lower() for c in insp.get_columns(table_name)}
        if column_name.lower() not in present:
            continue
        _dm_alter_column_null(bind, table_name, column_name)


def downgrade() -> None:
    # 降级不回滚 nullable，避免用户数据重新触发非空约束
    pass
