"""APScheduler 封装：注册/热更新/移除调度。

原实现只在启动时 sync 一次，运行期新建/编辑的调度不生效（必须重启）。
这里补上 upsert/remove，供调度路由增删改时即时调用。
"""
from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

TZ = ZoneInfo("Asia/Shanghai")

_scheduler = BackgroundScheduler(timezone=TZ)
_runner = None  # 由 startup.py 注册的批量运行函数 (db, scope, category_id, indicator_ids, date_option)


def set_runner(func) -> None:
    global _runner
    _runner = func


def build_trigger(frequency: str, run_time: str) -> CronTrigger | None:
    try:
        parts = run_time.split(":")
        h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    except Exception:
        h, m = 2, 0
    if frequency == "日":
        return CronTrigger(day_of_week="*", hour=h, minute=m, timezone=TZ)
    if frequency == "周":
        # 周频率固定周日运行，统计本周一到本周日
        return CronTrigger(day_of_week="sun", hour=h, minute=m, timezone=TZ)
    if frequency == "月":
        # 月频率固定月末运行
        return CronTrigger(day="last", hour=h, minute=m, timezone=TZ)
    if frequency == "季度":
        # 季度频率在 3/6/9/12 月末运行
        return CronTrigger(month="3,6,9,12", day="last", hour=h, minute=m, timezone=TZ)
    if frequency == "年":
        # 年频率在 12 月末运行
        return CronTrigger(month="12", day="last", hour=h, minute=m, timezone=TZ)
    return None  # 手动，不自动触发


def run_schedule_job(schedule_id: str) -> None:
    if not _runner:
        return
    from app.entity.models import Schedule
    from app.utils.database import SessionLocal

    db = SessionLocal()
    try:
        schedule = db.get(Schedule, schedule_id)
        if not schedule or not schedule.enabled:
            return
        indicator_ids = [schedule.indicator_id] if schedule.scope in ("selected", "") else []
        date_option = json.loads(schedule.date_option) if schedule.date_option else None
        _runner(db, schedule.scope or "selected", schedule.category_id or "", indicator_ids, date_option)
        schedule.last_run_at = datetime.now()
        schedule.next_run_at = next_run_time(schedule.frequency, schedule.run_time)
        db.commit()
    finally:
        db.close()


def _job_id(schedule_id: str) -> str:
    return f"sch_{schedule_id}"


def upsert(schedule_id: str) -> None:
    """注册或更新一个调度为 APScheduler job（幂等）。禁用或无触发器的调度会被移除。"""
    from app.entity.models import Schedule
    from app.utils.database import SessionLocal

    db = SessionLocal()
    try:
        schedule = db.get(Schedule, schedule_id)
        if not schedule or not schedule.enabled:
            remove(schedule_id)
            return
        trigger = build_trigger(schedule.frequency, schedule.run_time)
        if not trigger:
            remove(schedule_id)
            return
        _scheduler.add_job(
            run_schedule_job,
            trigger,
            args=[schedule.id],
            id=_job_id(schedule.id),
            replace_existing=True,
            misfire_grace_time=3600,
        )
    finally:
        db.close()


def remove(schedule_id: str) -> None:
    """从 APScheduler 移除调度 job（不存在则忽略）。"""
    job = _scheduler.get_job(_job_id(schedule_id))
    if job:
        _scheduler.remove_job(_job_id(schedule_id))


def next_run_time(frequency: str, run_time: str) -> datetime | None:
    """按频度/时刻计算下一次触发时间（无自动触发器则 None）。返回 naive 本地时区时间。"""
    trigger = build_trigger(frequency, run_time)
    if not trigger:
        return None
    fire = trigger.get_next_fire_time(None, datetime.now(TZ))
    return fire.replace(tzinfo=None) if fire else None


def sync_schedules() -> None:
    """把当前启用的调度全部注册（启动时调用；运行期新增/编辑走 upsert）。"""
    from app.entity.models import Schedule
    from app.utils.database import SessionLocal

    db = SessionLocal()
    try:
        for schedule in db.query(Schedule).filter(Schedule.enabled == True).all():  # noqa: E712
            upsert(schedule.id)
    finally:
        db.close()


def start() -> None:
    if not _scheduler.running:
        _scheduler.start()


def shutdown() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)