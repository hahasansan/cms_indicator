from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.migrations import run_migrations
from app.db import check_database_connection, get_db
from app.models import DataModel
from app.routers import health, indicators, jobs, models, reports, results, schedules, sql, dict_, _indicator_transfer
from app.seed import init_database
from app.services import scheduler as sched
from app.services.report_engine import detect_biz_date
from app.services.runner import run_batch_indicators

@asynccontextmanager
async def lifespan(app_):
    """应用生命周期：启动=建连+迁移+初始化+调度；关闭=停止调度。"""
    setup_logging()
    check_database_connection()
    run_migrations()
    db = next(get_db())
    try:
        if not settings.is_local:
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


app = FastAPI(title="指标管理系统 Pro", version="1.0.0", lifespan=lifespan)
logger = get_logger("main")
# CORS：默认允许所有来源；配置 CORS_ORIGINS 后收紧。通配 * 时不允许带凭据。
_cors_origins = list(settings.cors_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials="*" not in _cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request, call_next):
    import time

    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("%s %s -> %s (%.1fms)", request.method, request.url.path, response.status_code, duration_ms)
    return response


for _router in (
    health.router,
    models.router,
    dict_.router,
    reports.router,
    sql.router,
    indicators.router,
    _indicator_transfer.router,
    results.router,
    schedules.router,
    jobs.router,
):
    app.include_router(_router, prefix="/api")


# ---------------------------------------------------------------------------
# 启动流程：连接检查 + Alembic 迁移（schema 由 alembic baseline + 增量迁移负责）
# ---------------------------------------------------------------------------
def backfill_report_models(db: Session) -> None:
    """给存量报表模型回填 source_template 与业务日期自动识别（幂等，仅在达梦模式有 RP_REPORT）。"""
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
