"""统一结果表 T_IND_RESULT 物理落库。

契约：
- 固定表 T_IND_RESULT：RESULT_ID + INDICATOR_CODE + RUN_ID + FIELD1..FIELD25 (VARCHAR(255))
- 维度别名按序占 FIELD1..，度量别名按序占后续 FIELD 列，全部以字符串存储
- field_map_json（别名→FIELD列名 映射）存于 indicators 表，不在结果表
- 重算语义：按 RUN_ID 删除旧行后插入新行

说明：物理表由迁移脚本建好，运行时不再建表/补列。
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.utils import new_id

UNIFIED_TABLE = "T_IND_RESULT"
FIELD_COUNT = 25


def build_field_map(dim_aliases: list[str], metric_aliases: list[str]) -> dict[str, str]:
    """构建别名→FIELD列名映射，维度在前度量在后。

    返回 {"维度别名1": "FIELD1", ..., "度量别名1": "FIELDN", ...}
    """
    field_map: dict[str, str] = {}
    idx = 0
    for alias in dim_aliases:
        idx += 1
        if idx > FIELD_COUNT:
            raise ValueError(f"维度+度量列数超过预留 {FIELD_COUNT} 列上限")
        field_map[alias] = f"FIELD{idx}"
    for alias in metric_aliases:
        idx += 1
        if idx > FIELD_COUNT:
            raise ValueError(f"维度+度量列数超过预留 {FIELD_COUNT} 列上限")
        field_map[alias] = f"FIELD{idx}"
    return field_map


def rows_to_wide(rows: list[dict], field_map: dict[str, str]) -> list[dict]:
    """原始查询行 → 统一表 FIELD 列宽行，全部转字符串。"""
    wide: list[dict] = []
    for row in rows:
        item: dict = {}
        for alias, field_col in field_map.items():
            value = row.get(alias)
            item[field_col] = "" if value is None else str(value)
        wide.append(item)
    return wide


def write_results(
    db: Session,
    indicator_code: str,
    run_id: str,
    wide_rows: list[dict],
) -> int:
    """按 RUN_ID 删除旧行，插入新行到 T_IND_RESULT。返回写入行数。"""
    # 重算语义：按 RUN_ID 删除旧行
    db.execute(
        text(f'DELETE FROM "{UNIFIED_TABLE}" WHERE "RUN_ID" = :run_id'),
        {"run_id": run_id},
    )
    if not wide_rows:
        return 0

    # 收集所有出现的 FIELD 列（有序）
    field_cols = sorted(
        {key for row in wide_rows for key in row},
        key=lambda f: int(f[5:]),
    )
    columns = ['"RESULT_ID"', '"INDICATOR_CODE"', '"RUN_ID"'] + [f'"{c}"' for c in field_cols]
    param_keys = ['result_id', 'code', 'run_id'] + [c.lower() for c in field_cols]
    statement = text(
        f'INSERT INTO "{UNIFIED_TABLE}" ({", ".join(columns)}) '
        f'VALUES ({", ".join(f":{k}" for k in param_keys)})'
    )
    for row in wide_rows:
        params: dict = {
            "result_id": new_id("res"),
            "code": indicator_code,
            "run_id": run_id,
        }
        for col in field_cols:
            params[col.lower()] = row.get(col, "")
        db.execute(statement, params)
    return len(wide_rows)


def save_field_map(db: Session, indicator_id: str, field_map: dict[str, str]) -> None:
    """将 field_map 存入 indicators.field_map_json。"""
    db.execute(
        text('UPDATE indicators SET "FIELD_MAP_JSON" = :fm, "UPDATED_AT" = CURRENT_TIMESTAMP WHERE "ID" = :id'),
        {"fm": json.dumps(field_map, ensure_ascii=False), "id": indicator_id},
    )

