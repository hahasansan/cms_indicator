from __future__ import annotations

from datetime import date, datetime, timedelta

DATE_FMT = "%Y-%m-%d"


def _parse(value: str) -> date:
    return datetime.strptime(value, DATE_FMT).date()


def _last_workday(d: date) -> date:
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def resolve_single(option: str, value: str = "", ref: date | None = None) -> str:
    """余额类单日期：today / t1 / last_workday / specific(具体日期)。"""
    ref = ref or date.today()
    if option == "today":
        d = ref
    elif option == "t1":
        d = ref - timedelta(days=1)
    elif option == "last_workday":
        d = _last_workday(ref - timedelta(days=1))
    else:
        d = _parse(value)
    return d.strftime(DATE_FMT)


def resolve_start(option: str, value: str = "", ref: date | None = None) -> str:
    """时段类开始：month_start / prev_month_start / year_start / month(YYYY-MM) / specific。"""
    ref = ref or date.today()
    if option == "month_start":
        d = ref.replace(day=1)
    elif option == "prev_month_start":
        d = (ref.replace(day=1) - timedelta(days=1)).replace(day=1)
    elif option == "year_start":
        d = ref.replace(month=1, day=1)
    elif option == "month":
        y = int(value[:4])
        m = int(value[5:7])
        d = date(y, m, 1)
    else:
        d = _parse(value)
    return d.strftime(DATE_FMT)


def resolve_end(option: str, value: str = "", ref: date | None = None) -> str:
    """时段类结束：同余额类单日期选项。"""
    return resolve_single(option, value, ref)


def resolve_biz_dates(option: dict, ref: date | None = None) -> dict:
    """把前端选择的业务日期选项解析成实际日期。

    option 形如:
      {"type": "balance", "single": {"option": "today", "value": ""}}
      {"type": "period", "start": {"option": "month_start", "value": ""}, "end": {"option": "today", "value": ""}}
    返回:
      {"single": "YYYY-MM-DD"} 或 {"start": "...", "end": "..."}
    """
    ref = ref or date.today()
    if not option:
        raise ValueError("未指定业务日期")
    if option.get("type") == "period":
        start = option.get("start") or {}
        end = option.get("end") or {}
        return {
            "start": resolve_start(start.get("option", ""), start.get("value", ""), ref),
            "end": resolve_end(end.get("option", ""), end.get("value", ""), ref),
        }
    single = option.get("single") or {}
    return {"single": resolve_single(single.get("option", "today"), single.get("value", ""), ref)}
