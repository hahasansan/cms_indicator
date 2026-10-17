"""调度：CRUD、手动触发。"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import Depends, HTTPException, APIRouter
from sqlalchemy.orm import Session

from app.entity.models import Indicator, Schedule
from app.entity.schemas import ScheduleIn
from app.utils.database import get_db
from app.utils.serializers import schedule_to_dict
from app.services import scheduler as sched
from app.services.runner import run_batch_indicators
from app.utils.common import new_id

router = APIRouter(tags=["调度"])


def _apply_schedule_payload(schedule: Schedule, payload: ScheduleIn) -> None:
    schedule.indicator_id = payload.indicatorId
    schedule.name = payload.name
    schedule.frequency = payload.frequency
    schedule.run_time = payload.runTime
    schedule.enabled = payload.enabled
    schedule.date_option = json.dumps(payload.dateOption, ensure_ascii=False) if payload.dateOption else None
    schedule.scope = payload.scope
    schedule.category_id = payload.categoryId or None
    schedule.next_run_at = sched.next_run_time(schedule.frequency, schedule.run_time) if schedule.enabled else None


def _validate_schedule_payload(payload: ScheduleIn, db: Session) -> None:
    if not payload.name.strip():
        raise HTTPException(400, "调度名称不能为空")
    if payload.scope not in ("selected", "all", "category"):
        raise HTTPException(400, "调度范围不支持")
    if payload.scope == "selected" and not payload.indicatorId:
        raise HTTPException(400, "请选择指标")
    if payload.scope == "category" and not payload.categoryId:
        raise HTTPException(400, "请选择指标分类")
    if payload.indicatorId and not db.get(Indicator, payload.indicatorId):
        raise HTTPException(400, "指标不存在")


@router.get("/schedules")
def list_schedules(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(Schedule, Indicator.name).outerjoin(Indicator, Indicator.id == Schedule.indicator_id).all()
    return [schedule_to_dict(schedule, name or "") for schedule, name in rows]


@router.post("/schedules")
def create_schedule(payload: ScheduleIn, db: Session = Depends(get_db)) -> dict:
    _validate_schedule_payload(payload, db)
    schedule = Schedule(id=new_id("sch"))
    _apply_schedule_payload(schedule, payload)
    db.add(schedule)
    db.commit()
    sched.upsert(schedule.id)
    indicator = db.get(Indicator, schedule.indicator_id)
    return schedule_to_dict(schedule, indicator.name if indicator else "")


@router.put("/schedules/{schedule_id}")
def update_schedule(schedule_id: str, payload: ScheduleIn, db: Session = Depends(get_db)) -> dict:
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(404, "调度不存在")
    _validate_schedule_payload(payload, db)
    _apply_schedule_payload(schedule, payload)
    db.commit()
    sched.upsert(schedule.id)
    indicator = db.get(Indicator, schedule.indicator_id)
    return schedule_to_dict(schedule, indicator.name if indicator else "")


@router.post("/schedules/{schedule_id}/runs")
def run_schedule(schedule_id: str, db: Session = Depends(get_db)) -> dict:
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(404, "调度不存在")
    date_option = json.loads(schedule.date_option) if schedule.date_option else None
    indicator_ids = [schedule.indicator_id] if schedule.scope in ("selected", "") else []
    result = run_batch_indicators(db, schedule.scope or "selected", schedule.category_id or "", indicator_ids, date_option)
    schedule.last_run_at = datetime.now()
    schedule.next_run_at = sched.next_run_time(schedule.frequency, schedule.run_time) if schedule.enabled else None
    db.commit()
    return result


@router.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: str, db: Session = Depends(get_db)) -> dict:
    schedule = db.get(Schedule, schedule_id)
    if schedule:
        sched.remove(schedule.id)
        db.delete(schedule)
        db.commit()
    return {"ok": True}
