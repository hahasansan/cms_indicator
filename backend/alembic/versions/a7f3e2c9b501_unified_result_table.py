"""unified result table T_IND_RESULT

- DROP 旧表 T_IND_RESULT_D / T_IND_RESULT_M（历史数据丢失，已确认接受）
- CREATE 统一表 T_IND_RESULT（极简：RESULT_ID + INDICATOR_CODE + RUN_ID + FIELD1..25）
- job_runs.run_date 改名 single_date，加索引
- indicators 加 field_map_json CLOB 字段
- 清理 result_tables 元数据，登记 T_IND_RESULT
- 清空 result_table_fields 表（统一表字段固定）

达梦大小写敏感约定：
- 表名用无引号（达梦自动转大写，与 baseline 一致）
- 列名用大写 + 带引号
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision: str = "a7f3e2c9b501"
down_revision: Union[str, Sequence[str], None] = "f5a2c7e9d104"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"].upper() for column in inspect(op.get_bind()).get_columns(table)}


def _has_table(bind, name: str) -> bool:
    return bind.dialect.has_table(bind, name)


def upgrade() -> None:
    bind = op.get_bind()

    # ===== 1) DROP 旧物理结果表 =====
    for old_table in ("T_IND_RESULT_D", "T_IND_RESULT_M"):
        if _has_table(bind, old_table):
            bind.execute(text(f'DROP TABLE "{old_table}"'))

    # ===== 2) CREATE 统一表 T_IND_RESULT =====
    if not _has_table(bind, "T_IND_RESULT"):
        bind.execute(text(
            'CREATE TABLE "T_IND_RESULT" ('
            '"RESULT_ID" VARCHAR(64) NOT NULL,'
            '"INDICATOR_CODE" VARCHAR(64) NOT NULL,'
            '"RUN_ID" VARCHAR(64),'
            + ''.join(f'"FIELD{i}" VARCHAR(255),' for i in range(1, 26))
            + 'CONSTRAINT "PK_IND_RESULT" PRIMARY KEY("RESULT_ID"))'
        ))
    # 索引
    bind.execute(text('CREATE INDEX IF NOT EXISTS "IX_IND_RESULT_CODE" ON "T_IND_RESULT" ("INDICATOR_CODE")'))
    bind.execute(text('CREATE INDEX IF NOT EXISTS "IX_IND_RESULT_RUN"  ON "T_IND_RESULT" ("RUN_ID")'))

    # ===== 3) job_runs.run_date 改名 single_date =====
    if _has_table(bind, "job_runs"):
        present = _columns("job_runs")
        if "RUN_DATE" in present and "SINGLE_DATE" not in present:
            bind.execute(text('ALTER TABLE job_runs RENAME COLUMN "RUN_DATE" TO "SINGLE_DATE"'))
        # 加索引（point 类查询）
        bind.execute(text(
            'CREATE INDEX IF NOT EXISTS "IX_JOB_RUNS_IND_SINGLE" '
            'ON job_runs ("INDICATOR_ID", "SINGLE_DATE")'
        ))
        # 加索引（period 类查询）
        bind.execute(text(
            'CREATE INDEX IF NOT EXISTS "IX_JOB_RUNS_IND_PERIOD" '
            'ON job_runs ("INDICATOR_ID", "BUSINESS_START_DATE", "BUSINESS_END_DATE")'
        ))

    # ===== 4) indicators 加 field_map_json CLOB 字段 =====
    if _has_table(bind, "indicators"):
        present = _columns("indicators")
        if "FIELD_MAP_JSON" not in present:
            bind.execute(text('ALTER TABLE indicators ADD "FIELD_MAP_JSON" CLOB'))

    # ===== 5) 清理 result_tables 元数据，登记 T_IND_RESULT =====
    if _has_table(bind, "result_tables"):
        bind.execute(text(
            "DELETE FROM result_tables WHERE table_name IN ('T_IND_RESULT_D', 'T_IND_RESULT_M')"
        ))
        # 检查是否已登记统一表
        existing = bind.execute(text(
            "SELECT COUNT(*) FROM result_tables WHERE table_name = 'T_IND_RESULT'"
        )).scalar()
        if not existing:
            # 达梦大小写规则：普通列无引号会转大写匹配存储；保留字 comment 被建表时自动加小写引号，
            # 所以普通列用无引号，comment 用小写带引号
            bind.execute(text(
                "INSERT INTO result_tables (id, table_name, \"comment\", frequency, bound, source_id, schema_name, dimension_capacity, physical_status, last_check_message, created_at) "
                "VALUES ('rt_unified', 'T_IND_RESULT', '统一指标结果表', '通用', 1, NULL, 'INDICATOR', 25, 'ok', '统一表已建', CURRENT_TIMESTAMP)"
            ))

    # ===== 6) 清空 result_table_fields（统一表字段固定） =====
    if _has_table(bind, "result_table_fields"):
        bind.execute(text("DELETE FROM result_table_fields"))


def downgrade() -> None:
    """降级：DROP 统一表，恢复旧表结构（历史数据无法恢复）。"""
    bind = op.get_bind()
    if _has_table(bind, "T_IND_RESULT"):
        bind.execute(text('DROP TABLE "T_IND_RESULT"'))
    # 恢复旧表结构（空表，无历史数据）
    for old_table in ("T_IND_RESULT_D", "T_IND_RESULT_M"):
        if not _has_table(bind, old_table):
            bind.execute(text(
                f'CREATE TABLE "{old_table}" ('
                '"INDICATOR_CODE" VARCHAR(64) NOT NULL,'
                '"DATA_DATE" VARCHAR(16) NOT NULL,'
                '"RUN_ID" VARCHAR(64)'
                ')'
            ))
    # job_runs.single_date 改回 run_date
    if _has_table(bind, "job_runs"):
        present = _columns("job_runs")
        if "SINGLE_DATE" in present and "RUN_DATE" not in present:
            bind.execute(text('ALTER TABLE job_runs RENAME COLUMN "SINGLE_DATE" TO "RUN_DATE"'))
    # 删除 indicators.field_map_json
    if _has_table(bind, "indicators"):
        present = _columns("indicators")
        if "FIELD_MAP_JSON" in present:
            bind.execute(text('ALTER TABLE indicators DROP COLUMN "FIELD_MAP_JSON"'))
