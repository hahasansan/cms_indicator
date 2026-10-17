"""批量运行与运行记录。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.entity.models import JobRun
from app.entity.schemas import BatchRunIn
from app.utils.database import get_db
from app.utils.serializers import clean_dict, dt
from app.services.runner import run_batch_indicators

router = APIRouter(tags=["运行"])


@router.post("/batch-runs")
def batch_run(payload: BatchRunIn, db: Session = Depends(get_db)) -> dict:
    return run_batch_indicators(db, payload.scope, payload.categoryId, payload.indicatorIds, payload.dateOption)


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db)) -> list[dict]:
    return [clean_dict(row) | {"started_at": dt(row.started_at), "ended_at": dt(row.ended_at)} for row in db.query(JobRun).order_by(JobRun.started_at.desc()).limit(100).all()]