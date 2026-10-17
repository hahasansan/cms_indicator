from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import setup_logging
from app.core.migrations import run_migrations
from app.entity.models import DataModel
from app.services import scheduler as sched
from app.services.report_engine import detect_biz_date
from app.services.runner import run_batch_indicators
from app.utils.database import check_database_connection, get_db
from app.utils.seed import init_database


@asynccontextmanager
async def lifespan(app_):
    """应用生命周期：启动时准备数据库和调度，关闭时停止调度。"""
    setup_logging()
    check_database_connection()
    run_migrations()
    db = next(get_db())
    try:
        backfill_report_models(db)
        init_database(db)
    finally:
        db.close()
    sched.set_runner(run_batch_indicators)
    sched.sync_schedules()
    sched.start()
    try:
        yield
    finally:
        sched.shutdown()


def backfill_report_models(db: Session) -> None:
    """为存量报表模型回填 SQL 模板和业务日期识别配置。"""
    models = db.query(DataModel).filter(DataModel.source_type == "report", DataModel.source_template.is_(None)).all()
    for model in models:
        if not model.source_ref:
            continue
        row = db.execute(text("SELECT SQLTXT FROM RP_REPORT WHERE REPTID = :rid"), {"rid": model.source_ref}).first()
        if not row or not row[0]:
            continue
        model.source_template = str(row[0])
        biz = detect_biz_date(str(row[0]))
        if biz:
            model.biz_date_type = biz.get("type")
            model.biz_date_field = biz.get("field")
            model.biz_date_start_param = biz.get("start_param")
            model.biz_date_end_param = biz.get("end_param")
    db.commit()
