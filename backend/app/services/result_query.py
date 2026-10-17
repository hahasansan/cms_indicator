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


class PhysicalResultQuery:
    """从统一结果表查询并 pivot 回别名。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def fetch(self, indicators: list[Indicator], query: ResultQuery) -> ResultPage:
        rows: list[dict[str, Any]] = []
        for indicator in indicators:
            rows.extend(self._fetch_indicator(indicator, query))
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return ResultPage(rows=rows[start:end], page=query.page, page_size=query.page_size, has_more=len(rows) > end)

    def _fetch_indicator(self, indicator: Indicator, query: ResultQuery) -> list[dict[str, Any]]:
        # fieldMap：前端传优先，否则回退读 indicator.field_map_json
        field_map = query.field_map
        if not field_map and indicator.field_map_json:
            try:
                field_map = json.loads(indicator.field_map_json)
            except (json.JSONDecodeError, TypeError):
                field_map = {}
        if not field_map:
            return []

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
                values[alias] = row_dict.get(field_col.lower())
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
                "values": values,
            })
        return result
