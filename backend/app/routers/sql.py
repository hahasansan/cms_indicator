"""SQL 预览与试算：指标 SQL 生成预览、执行试算。"""
from __future__ import annotations

from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_dameng_config
from app.entity.models import DataModel
from app.utils.database import get_db
from app.routers.deps import build_indicator_sql
from app.entity.schemas import SqlPreviewIn
from app.services.biz_date import resolve_biz_dates
from app.services.dameng import query_rows as dm_query_rows
from app.services.sql_engine import biz_date_config

router = APIRouter(tags=["SQL 试算"])


def _apply_date_option(sql: str, config: dict, date_option: dict | None, db: Session) -> str:
    """把前端 dateOption 代入 SQL 中的业务时间占位符。"""
    biz = biz_date_config(config, None)
    model = None
    if config.get("modelId"):
        model = db.get(DataModel, str(config["modelId"]))
    if model:
        biz = biz_date_config(config, model)

    if not biz.get("start_param"):
        return sql
    if not date_option:
        raise HTTPException(400, "指标配置了业务时间参数，试算时必须选择业务日期")

    biz_dates = resolve_biz_dates(date_option)
    params: dict[str, str] = {}
    if biz.get("type") == "period":
        if biz.get("start_param") and biz_dates.get("start"):
            params[biz["start_param"]] = biz_dates["start"].replace("-", "")
        if biz.get("end_param") and biz_dates.get("end"):
            params[biz["end_param"]] = biz_dates["end"].replace("-", "")
    elif biz.get("start_param") and biz_dates.get("single"):
        params[biz["start_param"]] = biz_dates["single"].replace("-", "")

    for name, value in params.items():
        sql = sql.replace(f"':{name}'", f"'{value}'")
        sql = sql.replace(f":{name}", value)
    return sql


@router.post("/sql/previews")
def preview_sql(payload: SqlPreviewIn, db: Session = Depends(get_db)) -> dict:
    return {"sqlText": build_indicator_sql(db, payload.config)}


@router.post("/sql/trials")
def trial_sql(payload: SqlPreviewIn, db: Session = Depends(get_db)) -> dict:
    sql_text = build_indicator_sql(db, payload.config)
    sql_text = _apply_date_option(sql_text, payload.config, payload.dateOption, db)
    source = get_dameng_config()
    rows = dm_query_rows(source, sql_text)
    return {"sqlText": sql_text, "rows": rows[:10]}
