from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import get_logger
from app.routers import health, indicators, jobs, models, reports, results, schedules, sql, dict_, _indicator_transfer, measure_functions
from app.startup import lifespan


# FastAPI()创建 web应用
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

# web应用中间件：记录请求信息
@app.middleware("http")
async def log_requests(request, call_next):
    import time

    start = time.perf_counter()
    # 执行请求方法
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("%s %s -> %s (%.1fms)", request.method, request.url.path, response.status_code, duration_ms)
    return response


for _router in (
    health.router,
    models.router,
    measure_functions.router,
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
