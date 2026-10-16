"""字段类型/角色推断——全项目单一来源。

历史背景：report_engine.py 曾重复定义 _DATE_HINTS（第二份在模块级覆盖第一份）。
这里只保留被实际使用的第二份 hint 表（detect_biz_date 与 infer_field_type 一致），
避免再次出现"同名常量被覆盖"的隐蔽行为。
"""
from __future__ import annotations

# 字段名里出现这些关键字 → 判为日期/数值列（与 detect_biz_date 共用同一套口径）
_DATE_HINTS = (
    "date", "dt", "bgindt", "eddate", "matudt", "valudt", "recddt", "clendt",
    "opendt", "bktrdt", "inptdt", "issudt", "svdate", "systtm", "begdate",
    "buyin", "startdate", "enddate", "startdt", "enddt",
)
_NUM_HINTS = (
    "amt", "amount", "balance", "bala", "bondam", "faceam", "bargam", "bondol",
    "bookvalue", "cost", "income", "inrest", "yfamnt", "ourest", "inadam",
    "ysyjam", "pchgam", "delays", "daysum", "fincos", "tranam", "valtpv",
    "valtmd", "rate", "ir", "yield", "prc", "price", "wgrkpt", "ovtime",
    "num", "qty", "money", "sum", "count", "paymoney", "facevalue", "zmjjam",
    "tycbam", "inam", "ytm", "realrt", "cntrrt", "tranir", "bondir", "pyperd",
)

# 常见维度字段——按名字直接判维度
_DIMENSION_FIELDS = {
    "DATA_DATE",
    "ORG_ID",
    "BOND_TYPE",
    "BOND_RATING",
    "REMAIN_TERM",
    "PRODUCT_TYPE",
    "CURRENCY",
    "DIRECTION",
    "PRODUCT_CODE",
    "PRODUCT_NAME",
    "TENOR",
    "SOURCE_STATUS",
    "BOND_CODE",
    "BOND_NAME",
    "ACCOUNT_TYPE",
    "STATUS",
}

_NUMERIC_TYPE_MARKERS = ("REAL", "INTEGER", "NUMBER", "DECIMAL", "NUMERIC", "DOUBLE", "FLOAT", "BIGINT", "SMALLINT")


def infer_field_type(field_name: str) -> str:
    """字段类型按名字推断：NUMBER / DATE / VARCHAR。"""
    name = (field_name or "").lower()
    if any(hint in name for hint in _DATE_HINTS):
        return "DATE"
    if any(hint in name for hint in _NUM_HINTS):
        return "NUMBER"
    return "VARCHAR"


def dm_description_type_to_field(data_type: str) -> str:
    """把 dmPython description 返回的类型名映射为模型字段类型。"""
    t = (data_type or "").upper()
    if any(k in t for k in ("NUMBER", "DECIMAL", "INT", "FLOAT", "DOUBLE", "REAL", "BIGINT")):
        return "NUMBER"
    if any(k in t for k in ("DATE", "TIME", "TIMESTAMP")):
        return "DATE"
    return "VARCHAR"


def role_of(field_name: str, data_type: str) -> str:
    """字段角色：维度 / 度量 / 普通。"""
    normalized = (data_type or "").upper()
    if field_name in _DIMENSION_FIELDS:
        return "dimension"
    if any(item in normalized for item in _NUMERIC_TYPE_MARKERS):
        return "measure"
    return "normal"