"""Logical deletion helpers for indicators and their schedules."""
from __future__ import annotations

from datetime import datetime

from app.entity.models import Indicator
from app.services import scheduler


def soft_delete_indicator(indicator: Indicator) -> None:
    now = datetime.now()
    indicator.deleted_at = now
    indicator.updated_at = now
    for schedule in indicator.schedules:
        schedule.enabled = False
        schedule.next_run_at = None
        scheduler.remove(schedule.id)
