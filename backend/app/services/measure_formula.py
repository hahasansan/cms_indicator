"""Validation and SQL rendering for managed measure formulas."""
from __future__ import annotations

import re


_IDENTIFIER_PATTERN = r"(?:[^\W\d]|_)[\w$#]*"
_ASCII_IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_$#]*")
_TOKEN = re.compile(
    r"\s*(\{\d+\}|\{__[A-Z0-9_]+__\}|(?:\d+(?:\.\d*)?|\.\d+)|'(?:''|[^'])*'|"
    + _IDENTIFIER_PATTERN
    + r"|\|\||<=|>=|<>|!=|[()+\-*/%,.=<>])"
)
_PLACEHOLDER_IN_SOURCE = re.compile(r"('(?:''|[^'])*')|(\{__[A-Z0-9_]+__\})|(\{\d+\})")
# 允许的系统内置占位符（渲染时由 SQL 引擎注入）
_SYSTEM_PLACEHOLDERS = frozenset({"__BIZ_DAYS__"})
_KEYWORDS = {
    "ALL", "AND", "AS", "ASC", "BETWEEN", "CASE", "CURRENT", "DESC", "DISTINCT",
    "ELSE", "END", "FIRST", "FOLLOWING", "INTERVAL", "IS", "LAST", "NOT",
    "NULL", "NULLS", "OVER", "PARTITION", "PRECEDING", "RANGE", "ROW", "ROWS",
    "THEN", "UNBOUNDED", "WHEN", "ORDER", "BY", "DAY", "MONTH", "YEAR",
    "HOUR", "MINUTE", "SECOND",
    "SYSDATE", "CURRENT_DATE",
    "NUMBER", "DECIMAL", "NUMERIC", "INTEGER", "BIGINT", "SMALLINT",
    "VARCHAR", "VARCHAR2", "CHAR", "DATE", "TIMESTAMP", "FLOAT", "DOUBLE",
}
_FUNCTIONS = {
    "ABS", "AVG", "CAST", "CEIL", "CEILING", "COALESCE", "CONCAT", "COUNT",
    "DENSE_RANK", "DECODE", "EXP", "FLOOR", "GREATEST", "INSTR", "LAG",
    "LAST_DAY", "LAST_VALUE", "LEAD", "LEAST", "LENGTH", "LN", "LOG",
    "LOWER", "LTRIM", "MAX", "MIN", "MOD", "MONTHS_BETWEEN", "NANVL",
    "NTH_VALUE", "NTILE", "NULLIF", "NVL", "NVL2", "POWER", "RANK",
    "REPLACE", "ROUND", "ROW_NUMBER", "RTRIM", "SIGN", "SIN", "SQRT",
    "STDDEV", "SUBSTR", "SUBSTRING", "SUM", "TAN", "TO_CHAR", "TO_DATE",
    "TO_NUMBER", "TRIM", "TRUNC", "UPPER", "VARIANCE",
}


def formula_parameter_count(formula: str) -> int:
    """Validate a SQL expression template and return its sequential placeholder count.

    同时允许系统内置占位符 ``{__BIZ_DAYS__}`` 等，这些不计入字段参数数量，
    也不参与 1..N 连续性校验，渲染时由上层注入。
    """
    source = formula.strip()
    if not source or ";" in source or "--" in source or "/*" in source or "*/" in source:
        raise ValueError("公式不能为空，且不能包含 SQL 语句分隔符或注释")

    tokens: list[str] = []
    position = 0
    while position < len(source):
        match = _TOKEN.match(source, position)
        if not match:
            if source[position:].strip() == "":
                break
            raise ValueError(f"公式包含不支持的内容：{source[position:position + 16]}")
        tokens.append(match.group(1))
        position = match.end()

    if not tokens:
        raise ValueError("公式不能为空")
    depth = 0
    placeholders: set[int] = set()
    has_field_placeholder = False
    for index, token in enumerate(tokens):
        if token == "(":
            depth += 1
        elif token == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("公式括号不匹配")
        elif token.startswith("{") and token.endswith("}"):
            if token.startswith("{__"):
                # 系统内置占位符，完整名字含前后双下划线
                name = token[1:-1]  # {__XXX__} → __XXX__
                if name not in _SYSTEM_PLACEHOLDERS:
                    raise ValueError(f"不支持的系统占位符：{token}，可用占位符：{', '.join(sorted(_SYSTEM_PLACEHOLDERS))}")
                continue
            # 字段占位符 {n}
            number = int(token[1:-1])
            if number < 1:
                raise ValueError("公式参数从 {1} 开始编号")
            placeholders.add(number)
            has_field_placeholder = True
        elif re.fullmatch(_IDENTIFIER_PATTERN, token):
            if not _ASCII_IDENTIFIER_PATTERN.fullmatch(token):
                continue
            word = token.upper()
            is_function = index + 1 < len(tokens) and tokens[index + 1] == "("
            if word not in _KEYWORDS and not (is_function and word in _FUNCTIONS):
                raise ValueError(f"公式函数或关键字不支持：{token}")
    if depth:
        raise ValueError("公式括号不匹配")
    if not placeholders:
        # 纯系统占位符公式（如仅 {__BIZ_DAYS__}）允许；但必须有系统占位符
        if not has_field_placeholder:
            system_only = any(tok.startswith("{__") for tok in tokens)
            if not system_only:
                raise ValueError("公式至少需要一个字段参数（如 {1}）")
        return 0
    count = max(placeholders)
    if count > 25:
        raise ValueError("单个公式最多支持 25 个字段参数")
    if placeholders != set(range(1, count + 1)):
        raise ValueError("公式参数编号必须从 {1} 开始连续递增")
    return count


def render_measure_formula(
    formula: str,
    inputs: list[dict],
    field_expressions: list[str],
    system_placeholders: dict[str, str] | None = None,
) -> str:
    """渲染公式：先替换系统内置占位符，再替换字段占位符 {n}。"""
    expected_count = formula_parameter_count(formula)
    if expected_count > 0 and (len(inputs) != expected_count or len(field_expressions) != expected_count):
        raise ValueError(f"公式需要选择 {expected_count} 个字段")

    def _replace(match: re.Match[str]) -> str:
        if match.group(1):  # 字符串字面量，原样保留
            return match.group(1)
        if match.group(2):  # 系统内置占位符 {__XXX__}
            name = match.group(2)[1:-1]  # 去首尾花括号，得到 __XXX__
            if not system_placeholders or name not in system_placeholders:
                raise ValueError(f"公式包含系统占位符 {match.group(2)}，但未提供对应注入值")
            return f"({system_placeholders[name]})"
        # 字段占位符 {n}
        index = int(match.group(3)[1:-1]) - 1
        return f"({field_expressions[index]})"

    return _PLACEHOLDER_IN_SOURCE.sub(_replace, formula)
