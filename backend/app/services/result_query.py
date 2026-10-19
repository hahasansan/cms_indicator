"""统一结果表 T_IND_RESULT 查询。

JOIN job_runs 一步查询：T_IND_RESULT r ⋈ job_runs j ON r.RUN_ID = j.id
- 按 indicator_code + 业务日期范围过滤（period_type 决定用 single_date 还是 business_start/end_date）
- fieldMap 由前端传入（别名→FIELD列名），应用层 pivot 回别名
- 未传时回退读 indicator.field_map_json
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.entity.models import Indicator
from app.services.sql_engine import result_dimension_names, result_metric_names
from app.services.result_writer import UNIFIED_TABLE


@dataclass(frozen=True)
class ResultQuery:
    start_date: str = ""
    end_date: str = ""
    field_map: dict[str, str] | None = None  # 前端传入：别名→FIELD列名
    dimension_filters: dict[str, str] | None = None
    page: int = 1
    page_size: int = 100


@dataclass(frozen=True)
class ResultPage:
    rows: list[dict[str, Any]]
    page: int
    page_size: int
    has_more: bool
    dimension_columns: list[str]
    dimension_owners: dict[str, list[dict[str, str]]]
    measure_groups: list[dict[str, Any]]


class PhysicalResultQuery:
    """从统一结果表查询，并按完整维度组合合并多指标结果。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def fetch(
        self,
        indicators: list[Indicator],
        query: ResultQuery,
        combine_rows: bool = True,
    ) -> ResultPage:
        """查询所选指标，并可将相同期间、相同维度的记录合并为一行。

        先逐指标读取字段定义和结果，再按完整维度键合并；因此分页必须在
        合并和排序之后进行，否则不同指标的同一行可能被拆到不同页。
        combine_rows=False 用于单指标旧接口，保留原始逐指标结果结构。
        """
        indicator_rows: list[tuple[Indicator, list[dict[str, Any]], list[str], list[str]]] = []
        dimension_columns: set[str] = set()
        dimension_owners: dict[str, list[dict[str, str]]] = {}
        measure_groups: dict[tuple[str, ...], dict[str, Any]] = {}

        # 收集每个指标实际落库的维度、度量别名，并按指标自己的 field map 读取物理结果。
        for indicator in indicators:
            field_map = self._field_map(indicator, query)
            if not field_map:
                continue
            config = json.loads(indicator.config_json)
            dimensions = [
                alias for alias in result_dimension_names(config, self.db)
                if alias != "DATA_DATE" and alias in field_map
            ]
            measures = [
                alias for alias in result_metric_names(config)
                if alias in field_map
            ]
            dimensions = list(dict.fromkeys(dimensions))
            measures = list(dict.fromkeys(measures))
            dimension_columns.update(dimensions)
            for alias in dimensions:
                owners = dimension_owners.setdefault(alias, [])
                if not any(owner["indicatorId"] == indicator.id for owner in owners):
                    owners.append({
                        "indicatorId": indicator.id,
                        "indicatorName": indicator.name,
                    })
            group_key = tuple(sorted(dimensions))
            group = measure_groups.setdefault(group_key, {
                "key": json.dumps(group_key, ensure_ascii=False),
                "label": " / ".join(group_key) if group_key else "无维度",
                "dimensions": list(group_key),
                "columns": [],
            })
            group["columns"].extend({
                "key": self._measure_key(indicator.id, alias),
                "indicatorId": indicator.id,
                "alias": alias,
                "indicatorName": indicator.name,
                "indicatorCode": indicator.code,
            } for alias in measures)
            indicator_rows.append((
                indicator,
                self._fetch_indicator(indicator, query, field_map),
                dimensions,
                measures,
            ))

        # 单指标详情接口沿用原有返回格式，不执行跨指标宽表合并。
        if not combine_rows:
            raw_rows = [
                row
                for _, rows, _, _ in indicator_rows
                for row in rows
            ]
            start = (query.page - 1) * query.page_size
            end = start + query.page_size
            return ResultPage(
                rows=raw_rows[start:end],
                page=query.page,
                page_size=query.page_size,
                has_more=len(raw_rows) > end,
                dimension_columns=sorted(dimension_columns),
                dimension_owners=dimension_owners,
                measure_groups=[
                    measure_groups[group_key]
                    for group_key in sorted(measure_groups)
                ],
            )

        # 维度列是所有指标维度的并集。每条记录用“期间 + 所有维度值”作为键；
        # 某指标缺少某维度时该值为空，因此不同粒度的记录不会被错误合并。
        ordered_dimensions = sorted(dimension_columns)
        rows_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
        for indicator, rows, dimensions, measures in indicator_rows:
            for row in rows:
                dimension_values = {
                    alias: row["values"].get(alias)
                    if row["values"].get(alias) is not None else ""
                    for alias in dimensions
                }
                # Missing dimensions remain blank and are part of the key, so finer-grained
                # results are not accidentally joined to coarser-grained results.
                key_dimensions = tuple(
                    (
                        alias,
                        "" if dimension_values.get(alias) is None
                        else str(dimension_values[alias]),
                    )
                    for alias in ordered_dimensions
                )
                key = (
                    row["period_type"],
                    row["period_start"],
                    row["period_end"],
                    key_dimensions,
                )
                current = rows_by_key.get(key)
                if current is None:
                    current = {
                        "id": json.dumps(key, ensure_ascii=False, default=str),
                        "period_type": row["period_type"],
                        "data_date": row["data_date"],
                        "period_start": row["period_start"],
                        "period_end": row["period_end"],
                        "dimensions": {
                            alias: dimension_values.get(alias, "")
                            for alias in ordered_dimensions
                        },
                        "values": {},
                    }
                    rows_by_key[key] = current
                for alias in measures:
                    # 指标 ID 纳入度量键，避免不同指标使用同名度量别名时互相覆盖。
                    measure_key = self._measure_key(indicator.id, alias)
                    if measure_key not in current["values"]:
                        current["values"][measure_key] = row["values"].get(alias)

        # 固定排序后再分页，保证翻页稳定且分页单位是合并后的展示行。
        rows = sorted(
            rows_by_key.values(),
            key=lambda row: (
                tuple(
                    "" if row["dimensions"].get(alias) is None
                    else str(row["dimensions"][alias])
                    for alias in ordered_dimensions
                ),
                row["period_start"],
                row["period_end"],
                row["period_type"],
            ),
        )
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return ResultPage(
            rows=rows[start:end],
            page=query.page,
            page_size=query.page_size,
            has_more=len(rows) > end,
            dimension_columns=ordered_dimensions,
            dimension_owners=dimension_owners,
            measure_groups=[
                measure_groups[group_key]
                for group_key in sorted(measure_groups)
            ],
        )

    @staticmethod
    def _measure_key(indicator_id: str, alias: str) -> str:
        return f"{indicator_id}::{alias}"

    @staticmethod
    def _field_map(indicator: Indicator, query: ResultQuery) -> dict[str, str]:
        # fieldMap：前端传优先，否则回退读 indicator.field_map_json
        field_map = query.field_map
        if not field_map and indicator.field_map_json:
            try:
                field_map = json.loads(indicator.field_map_json)
            except (json.JSONDecodeError, TypeError):
                field_map = {}
        return field_map or {}

    def _fetch_indicator(
        self,
        indicator: Indicator,
        query: ResultQuery,
        field_map: dict[str, str],
    ) -> list[dict[str, Any]]:
        """按指标的字段映射读取物理列，并转换为别名形式的 API 记录。"""
        period_type = (indicator.period_type or "point").lower()
        field_cols = sorted(set(field_map.values()), key=lambda f: int(f[5:]))

        params: dict[str, Any] = {
            "indicator_code": indicator.code,
            "indicator_id": indicator.id,
        }
        date_cond = self._date_condition(period_type, query, params)

        select_parts = [f'r."{c}" AS "{c}"' for c in field_cols]
        select_parts.extend([
            'r."RUN_ID" AS "RUN_ID"',
            'j."SINGLE_DATE" AS "single_date"',
            'j."BUSINESS_START_DATE" AS "business_start_date"',
            'j."BUSINESS_END_DATE" AS "business_end_date"',
            'j."STATUS" AS "run_status"',
            'j."STARTED_AT" AS "started_at"',
        ])
        sql = (
            f'SELECT {", ".join(select_parts)} '
            f'FROM "{UNIFIED_TABLE}" r '
            f'JOIN job_runs j ON r."RUN_ID" = j."ID" '
            f'WHERE r."INDICATOR_CODE" = :indicator_code '
            f'AND j."INDICATOR_ID" = :indicator_id {date_cond}'
        )

        # 维度筛选（按别名→FIELD列）
        for idx, (alias, value) in enumerate((query.dimension_filters or {}).items()):
            field_col = field_map.get(alias)
            if not field_col:
                continue
            sql += f' AND LOWER(CAST(r."{field_col}" AS VARCHAR(255))) LIKE :dim_{idx}'
            params[f"dim_{idx}"] = f"%{value.lower()}%"

        sql += ' ORDER BY j."STARTED_AT" DESC'

        physical_rows = self.db.execute(text(sql), params).mappings().all()
        return self._to_api_rows(indicator, physical_rows, field_map, period_type)

    @staticmethod
    def _date_condition(period_type: str, query: ResultQuery, params: dict[str, Any]) -> str:
        """按 period_type 构建业务日期过滤条件。

        point：single_date 落在 [start, end] 内
        period：结果期间完整覆盖查询区间（business_start <= start AND business_end >= end）
        """
        cond = ""
        if period_type == "period":
            if query.start_date and query.end_date:
                cond = 'AND j."BUSINESS_START_DATE" <= :start_date AND j."BUSINESS_END_DATE" >= :end_date'
                params["start_date"] = query.start_date
                params["end_date"] = query.end_date
            elif query.start_date:
                cond = 'AND j."BUSINESS_END_DATE" >= :start_date'
                params["start_date"] = query.start_date
            elif query.end_date:
                cond = 'AND j."BUSINESS_START_DATE" <= :end_date'
                params["end_date"] = query.end_date
        else:
            if query.start_date and query.end_date:
                cond = 'AND j."SINGLE_DATE" >= :start_date AND j."SINGLE_DATE" <= :end_date'
                params["start_date"] = query.start_date
                params["end_date"] = query.end_date
            elif query.start_date:
                cond = 'AND j."SINGLE_DATE" >= :start_date'
                params["start_date"] = query.start_date
            elif query.end_date:
                cond = 'AND j."SINGLE_DATE" <= :end_date'
                params["end_date"] = query.end_date
        return cond

    @staticmethod
    def _to_api_rows(
        indicator: Indicator,
        physical_rows: list[Any],
        field_map: dict[str, str],
        period_type: str,
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for row in physical_rows:
            row_dict = {str(k): v for k, v in row.items()}
            run_id = row_dict.get("RUN_ID")
            single_date = str(row_dict.get("single_date") or "")
            biz_start = str(row_dict.get("business_start_date") or "")
            biz_end = str(row_dict.get("business_end_date") or "")
            # pivot：FIELD列 → 别名
            values: dict[str, Any] = {}
            for alias, field_col in field_map.items():
                values[alias] = row_dict.get(field_col, row_dict.get(field_col.lower()))
            result.append({
                "id": f"{indicator.code}:{run_id}:{single_date}",
                "indicator_code": indicator.code,
                "indicator_id": indicator.id,
                "indicator_name": indicator.name,
                "run_id": run_id,
                "period_type": period_type,
                "data_date": single_date,
                "period_start": biz_start or single_date,
                "period_end": biz_end or single_date,
                "period_type": period_type,
                "values": values,
            })
        return result
