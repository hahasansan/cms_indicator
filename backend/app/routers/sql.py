"""SQL 预览与试算：指标 SQL 生成预览、执行试算。"""
from __future__ import annotations

from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session

from app.core.config import get_dameng_config
from app.db import get_db
from app.routers.deps import build_indicator_sql
from app.schemas import SqlPreviewIn
from app.services.dameng import query_rows as dm_query_rows

router = APIRouter(tags=["SQL 试算"])


@router.post("/sql/previews")
def preview_sql(payload: SqlPreviewIn, db: Session = Depends(get_db)) -> dict:
    return {"sqlText": build_indicator_sql(db, payload.config)}


@router.post("/sql/trials")
def trial_sql(payload: SqlPreviewIn, db: Session = Depends(get_db)) -> dict:
    sql_text = build_indicator_sql(db, payload.config)
    source = get_dameng_config()
    rows = dm_query_rows(source, sql_text)
    return {"sqlText": sql_text, "rows": rows[:10]}
