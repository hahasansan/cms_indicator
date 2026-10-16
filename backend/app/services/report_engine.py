from __future__ import annotations

import re

from app.services.type_inference import _DATE_HINTS

# 报表 SQL 里的可选参数块，形如 [and b.bondcd = ':bondcd']
BRACKET_RE = re.compile(r"\[[^\]]*\]")
# 参数占位符 :xxx
PARAM_RE = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")
# 条件块里的 字段 运算符 参数
_COND_RE = re.compile(r"\[\s*and\s+([a-z0-9_\.]+)\s*(>=|<=|=|<>|!=|>|<|BETWEEN|LIKE)\s*'?:?([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE)
_BETWEEN_RE = re.compile(r"BETWEEN\s+'?:?([a-zA-Z_][a-zA-Z0-9_]*)'?\s+AND\s+'?:?([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE)
_FUNC_HINTS = ('to_date', 'to_char', 'months_between', 'add_months', 'last_day', 'trunc', 'nvl')

# 注意：_DATE_HINTS 来自 type_inference 的单一来源（不再在本文件重复定义，避免同名覆盖）。


def detect_biz_date(sql_text: str) -> dict | None:
    """自动识别报表的业务日期参数。

    返回 {type: 'balance'|'period', field, start_param, end_param} 或 None。
    balance=余额类(日期=单时点)；period=时段类(日期区间，起止两个参数)。
    """
    sql = sql_text or ""
    blocks = BRACKET_RE.findall(sql)
    stripped = BRACKET_RE.sub("", sql)
    mandatory = set(PARAM_RE.findall(stripped))

    date_eq: dict[str, str] = {}     # param -> field
    date_range: dict[str, tuple[str, str]] = {}  # param -> (op, field)
    for block in blocks:
        for m in _BETWEEN_RE.finditer(block):
            date_range[m.group(1)] = (">=", "?")
            date_range[m.group(2)] = ("<", "?")
        for m in _COND_RE.finditer(block):
            field, op, pname = m.group(1).lower(), m.group(2).upper(), m.group(3)
            if field in _FUNC_HINTS:
                continue
            if any(h in field for h in _DATE_HINTS):
                if op == "=":
                    date_eq[pname] = field
                else:
                    date_range[pname] = (op, field)

    if date_range:
        start = next(((p, f) for p, (op, f) in date_range.items() if op in (">=", ">")), None)
        end = next(((p, f) for p, (op, f) in date_range.items() if op in ("<=", "<")), None)
        field = (start[1] if start and start[1] != "?" else (end[1] if end and end[1] != "?" else None))
        return {"type": "period", "field": field, "start_param": start[0] if start else None, "end_param": end[0] if end else None}
    if date_eq:
        param = next(iter(date_eq))
        return {"type": "balance", "field": date_eq[param], "start_param": param, "end_param": None}
    # 兜底：必填参数(报表系统里必填多为日期)按数量推断
    if mandatory:
        mlist = sorted(mandatory)
        if len(mlist) >= 2:
            return {"type": "period", "field": None, "start_param": mlist[0], "end_param": mlist[1]}
        return {"type": "balance", "field": None, "start_param": mlist[0], "end_param": None}
    return None


def resolve_report_for_date(template: str | None, biz_date_info: dict | None, dates: dict) -> str:
    """按业务日期代入报表 SQL 模板。

    保留并代入业务日期参数(single / start / end)，去掉其他不含业务日期的可选块。
    biz_date_info: {type, field, start_param, end_param}
    dates: {'single': '...'} 或 {'start': '...', 'end': '...'}
    """
    if not template:
        return (template or "").strip().rstrip(";")
    params: dict[str, str] = {}
    if biz_date_info:
        if biz_date_info.get("type") == "period":
            if biz_date_info.get("start_param"):
                params[biz_date_info["start_param"]] = dates.get("start", "")
            if biz_date_info.get("end_param"):
                params[biz_date_info["end_param"]] = dates.get("end", "")
        else:
            if biz_date_info.get("start_param"):
                params[biz_date_info["start_param"]] = dates.get("single", "")

    def _sub(sql: str) -> str:
        for name, val in params.items():
            sql = sql.replace(f"':{name}'", f"'{val}'")
            sql = sql.replace(f":{name}", val)
        return sql

    def _process(block_match) -> str:
        block = block_match.group(0)
        if not any(p in params.keys() for p in PARAM_RE.findall(block)):
            return ""  # 不含业务日期的可选块，去掉
        return _sub(block)[1:-1]  # 保留并去掉 [ ]

    result = BRACKET_RE.sub(_process, template)
    result = _sub(result)
    return result.strip().rstrip(";")


def report_params(sql_text: str) -> dict:
    """解析报表 SQL 中的参数。

    optional: 只出现在 [可选块] 里的参数(导入时可去掉,不填值)
    mandatory: 出现在括号外正文里的参数——即使同时也在可选块里出现，
                正文那处仍必须填值才能跑
    """
    sql = sql_text or ""
    optional = set()
    for block in BRACKET_RE.findall(sql):
        optional.update(PARAM_RE.findall(block))
    stripped = BRACKET_RE.sub("", sql)
    mandatory = sorted(set(PARAM_RE.findall(stripped)))
    return {"optional": sorted(optional), "mandatory": mandatory}


def extract_optional_param_fields(sql_text: str, biz_date_info: dict | None) -> list[dict]:
    """从可选块里提取非业务日期的参数字段。

    返回 [{field_name, param_name, op}, ...]，field_name 取字段名的最后一段（a.dept -> dept）。
    这些字段对应报表 SQL 里 [and field = ':param'] 形式的可选筛选条件，
    解析为数据模型的维度字段供指标层使用。
    """
    biz_params = set()
    if biz_date_info:
        if biz_date_info.get("start_param"):
            biz_params.add(biz_date_info["start_param"])
        if biz_date_info.get("end_param"):
            biz_params.add(biz_date_info["end_param"])

    fields: list[dict] = []
    seen: set[str] = set()
    for block in BRACKET_RE.findall(sql_text or ""):
        for m in _COND_RE.finditer(block):
            field_raw, op, pname = m.group(1), m.group(2).upper(), m.group(3)
            field_name = field_raw.split(".")[-1]
            if pname in biz_params or field_name.lower() in seen:
                continue
            seen.add(field_name.lower())
            fields.append({"field_name": field_name, "param_name": pname, "op": op})
    return fields


def validate_report_params(sql_text: str, params: dict | None) -> None:
    """必填参数(括号外)缺失时抛出 ValueError。"""
    missing = [m for m in report_params(sql_text)["mandatory"] if not str((params or {}).get(m) or "").strip()]
    if missing:
        raise ValueError(f"请填写报表必填参数：{', '.join(missing)}")


def resolve_report_sql(sql_text: str, params: dict | None) -> str:
    """去掉所有 [可选参数块]，代入用户填的必填参数，返回可执行的基础 SQL(不带末尾分号)。

    代入同时处理两种写法：
      ':bgdate'  ->  '20260710'   (参数在引号内)
      :bgdate    ->  20260710     (裸参数)
    """
    sql = BRACKET_RE.sub("", sql_text or "")
    for name, value in (params or {}).items():
        text = str(value).strip()
        if not text:
            continue
        sql = sql.replace(f"':{name}'", f"'{text}'")
        sql = sql.replace(f":{name}", text)
    return sql.strip().rstrip(";")