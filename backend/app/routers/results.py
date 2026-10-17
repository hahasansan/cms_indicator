"""指标结果查询路由。"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.entity.models import Indicator
from app.utils.database import get_db
from app.utils.serializers import indicator_to_dict
from app.services.result_query import PhysicalResultQuery, ResultQuery

router = APIRouter(tags=["结果"])

DATE_FORMAT = "%Y-%m-%d"


def _selected_indicators(indicator_ids: str, db: Session) -> list[Indicator]:
    ids = list(dict.fromkeys(item.strip() for item in indicator_ids.split(",") if item.strip()))
    if not ids:
        return []
    indicators = db.query(Indicator).filter(Indicator.id.in_(ids)).all()
    if len(indicators) != len(ids):
        raise HTTPException(400, "存在不存在的指标")
    return indicators


def _build_query(
    start_date: str,
    end_date: str,
    dimension_filters: str,
    field_map_json: str,
    page: int,
    page_size: int,
) -> ResultQuery:
    for name, value in (("startDate", start_date), ("endDate", end_date)):
        if not value:
            continue
        try:
            datetime.strptime(value, DATE_FORMAT)
        except ValueError as exc:
            raise HTTPException(400, f"{name} 日期格式应为 YYYY-MM-DD") from exc
    if start_date and end_date and start_date > end_date:
        raise HTTPException(400, "数据日期起始日不能晚于结束日")
    try:
        raw_filters = json.loads(dimension_filters) if dimension_filters else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "维度筛选条件格式错误") from exc
    filters = {str(key): str(value).strip().lower() for key, value in raw_filters.items() if str(value).strip()}
    field_map: dict[str, str] | None = None
    if field_map_json:
        try:
            field_map = json.loads(field_map_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(400, "fieldMap 格式错误") from exc
    return ResultQuery(
        start_date=start_date,
        end_date=end_date,
        field_map=field_map,
        dimension_filters=filters,
        page=max(1, page),
        page_size=max(1, min(page_size, 500)),
    )


@router.get(
    "/indicator-results",
    summary="查询指标结果明细",
    description=(
        "按指定指标、日期范围和维度过滤条件分页查询指标结果。\n\n"
        "支持传入多个指标 ID，按维度筛选过滤结果，并可通过 fieldMap 控制返回字段与展示字段之间的映射。"
    ),
)
def query_indicator_results(
    indicatorIds: str = Query(
        "",
        description="指标 ID 列表，多个以英文逗号分隔，例如：'101,102,103'",
    ),
    startDate: str = Query(
        "",
        description="查询开始日期，格式 YYYY-MM-DD；可为空表示不限制起始日",
    ),
    endDate: str = Query(
        "",
        description="查询结束日期，格式 YYYY-MM-DD；可为空表示不限制结束日",
    ),
    dimensionFilters: str = Query(
        "",
        description="维度筛选条件 JSON 字符串，例如：'{\"region\":\"上海\",\"dept\":\"研发部\"}'",
    ),
    fieldMap: str = Query(
        "",
        description="返回字段映射 JSON 字符串，常用于字段名称转换或前端展示映射",
    ),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    pageSize: int = Query(100, ge=1, le=500, description="每页条数，范围 1-500"),
    db: Session = Depends(get_db),
) -> dict:
    """查询指标结果记录，支持指标组合、日期过滤、维度筛选和分页。"""
    indicators = _selected_indicators(indicatorIds, db)
    if not indicators:
        return {"indicators": [], "rows": [], "page": 1, "pageSize": pageSize, "hasMore": False}
    query = _build_query(startDate, endDate, dimensionFilters, fieldMap, page, pageSize)
    result_page = PhysicalResultQuery(db).fetch(indicators, query)
    return {
        "indicators": [indicator_to_dict(indicator) for indicator in indicators],
        "rows": result_page.rows,
        "page": result_page.page,
        "pageSize": result_page.page_size,
        "hasMore": result_page.has_more,
    }


@router.get("/indicators/{indicator_id}/results")
def indicator_results(indicator_id: str, db: Session = Depends(get_db)) -> dict:
    indicator = db.get(Indicator, indicator_id)
    if not indicator:
        raise HTTPException(404, "指标不存在")
    result_page = PhysicalResultQuery(db).fetch([indicator], ResultQuery(page_size=200))
    return {"indicator": indicator_to_dict(indicator), "rows": result_page.rows, "hasMore": result_page.has_more}
