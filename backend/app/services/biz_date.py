from __future__ import annotations

from datetime import date, datetime, timedelta

DATE_FMT = "%Y-%m-%d"


def _parse(value: str) -> date:
    if not value or not value.strip():
        raise ValueError("日期值不能为空")
    return datetime.strptime(value.strip(), DATE_FMT).date()


def _last_workday(d: date) -> date:
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def resolve_single(option: str, value: str = "", ref: date | None = None) -> str:
    """余额类单日期：today / t1 / last_workday / specific(具体日期)。"""
    ref = ref or date.today()
    option = option or "today"
    if option == "today":
        d = ref
    elif option == "t1":
        d = ref - timedelta(days=1)
    elif option == "last_workday":
        d = _last_workday(ref - timedelta(days=1))
    elif option == "specific":
        d = _parse(value)
    else:
        # 未知 option 兜底当作 today
        d = ref
    return d.strftime(DATE_FMT)


def resolve_start(option: str, value: str = "", ref: date | None = None) -> str:
    """时段类开始：week_start / month_start / quarter_start / year_start / month(YYYY-MM) / specific。"""
    ref = ref or date.today()
    option = option or "month_start"
    if option == "week_start":
        d = ref - timedelta(days=ref.weekday())
    elif option == "month_start":
        d = ref.replace(day=1)
    elif option == "quarter_start":
        d = date(ref.year, ((ref.month - 1) // 3) * 3 + 1, 1)
    elif option == "year_start":
        d = ref.replace(month=1, day=1)
    elif option == "month":
        if not value:
            raise ValueError("月份值不能为空")
        y = int(value[:4])
        m = int(value[5:7])
        d = date(y, m, 1)
    elif option == "specific":
        d = _parse(value)
    else:
        d = ref.replace(day=1)
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
            "start": resolve_start(start.get("option", "month_start"), start.get("value", ""), ref),
            "end": resolve_end(end.get("option", "today"), end.get("value", ""), ref),
        }
    single = option.get("single") or {}
    return {"single": resolve_single(single.get("option", "today"), single.get("value", ""), ref)}
