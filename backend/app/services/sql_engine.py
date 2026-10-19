from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.entity.models import DataModel, Indicator
from app.services.result_writer import FIELD_COUNT


DERIVATIVE_LABELS = {
    "dod_delta": "较上期增量",
    "dod_growth": "较上期增幅",
    "cumulative": "累计值",
    "rank_desc": "排名",
    "prev_day_value": "较上日值",
    "prev_day_growth": "较上日增幅(%)",
    "prev_month_value": "较上月值",
    "prev_month_growth": "较上月增幅(%)",
    "year_start_comparison_value": "较年初值",
    "year_start_comparison_growth": "较年初增幅(%)",
    "prev_year_value": "较去年同期值",
    "prev_year_growth": "较去年同期增幅(%)",
    "month_cumulative": "月累计",
    "quarter_cumulative": "季累计",
    "year_cumulative": "年累计",
    "month_average": "月均值",
    "quarter_average": "季均值",
    "year_average": "年均值",
    "month_start_value": "月初值",
    "quarter_start_value": "季初值",
    "year_start_value": "年初值",
    "month_end_value": "月末值",
    "quarter_end_value": "季末值",
    "year_end_value": "年末值",
}


DATE_BASED_DERIVATIVES = {
    "prev_day_value",
    "prev_day_growth",
    "prev_month_value",
    "prev_month_growth",
    "year_start_comparison_value",
    "year_start_comparison_growth",
    "prev_year_value",
    "prev_year_growth",
    "month_cumulative",
    "quarter_cumulative",
    "year_cumulative",
    "month_average",
    "quarter_average",
    "year_average",
    "month_start_value",
    "quarter_start_value",
    "year_start_value",
    "month_end_value",
    "quarter_end_value",
    "year_end_value",
}


def derivative_alias(measure_alias: str, derivative: str) -> str:
    return f"{measure_alias}_{DERIVATIVE_LABELS.get(derivative, derivative)}"


def quote_alias(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


NUMERIC_TYPES = ("INTEGER", "NUMBER", "DECIMAL", "NUMERIC", "DOUBLE", "FLOAT", "REAL", "BIGINT", "SMALLINT")


def is_numeric_type(data_type: str) -> bool:
    normalized = (data_type or "").upper()
    return any(item in normalized for item in NUMERIC_TYPES)


def quote_value(value: object, numeric: bool = False) -> str:
    value_text = "" if value is None else str(value).strip()
    if numeric:
        if not value_text:
            raise ValueError("数值筛选条件不能为空")
        try:
            number = Decimal(value_text)
        except InvalidOperation as exc:
            raise ValueError(f"筛选值“{value_text}”不是有效数字") from exc
        if not number.is_finite():
            raise ValueError("筛选值必须是有限数字")
        return value_text
    return "'" + value_text.replace("'", "''") + "'"


def sql_field(name: str, alias: str = "a") -> str:
    return name if "." in name or "(" in name else f"{alias}.{name}"


def model_table_expr(model: DataModel) -> str:
    """报表及自定义 SQL 模型用子查询，普通模型使用物理表名。"""
    if getattr(model, "source_type", "table") in {"report", "custom_sql"} and model.source_sql:
        return f"({model.source_sql})"
    return model.table_name


def filter_sql(item: dict, field_types: dict[str, str], config: dict | None = None, main_model_id: str = "") -> str:
    field_name = str(item.get("fieldName") or "")
    if field_name not in field_types:
        raise ValueError(f"筛选字段“{field_name}”不存在")
    alias = alias_of_model(config or {}, str(item.get("modelId") or ""), main_model_id) if config else "a"
    field = sql_field(field_name, alias)
    numeric = is_numeric_type(field_types[field_name])
    op = str(item.get("operator") or "=").upper()
    if op not in {"=", "!=", "<>", ">", ">=", "<", "<=", "LIKE", "IN"}:
        raise ValueError("不支持的筛选操作符")
    value = item.get("value", "")
    if op == "LIKE":
        return f"{field} LIKE {quote_value('%' + str(value) + '%')}"
    if op == "IN":
        raw_values = [part.strip() for part in str(value).split(",") if part.strip()]
        if not raw_values:
            raise ValueError("IN 筛选条件至少需要一个值")
        values = ", ".join(quote_value(part, numeric) for part in raw_values)
        return f"{field} IN ({values})"
    return f"{field} {op} {quote_value(value, numeric)}"


def filter_join(item: dict) -> str:
    join_with = str(item.get("joinWith") or "AND").upper()
    if join_with not in {"AND", "OR"}:
        raise ValueError("筛选条件连接方式只能是 AND 或 OR")
    return join_with


def measures_of(config: dict) -> list[dict]:
    if config.get("measures"):
        return config["measures"]
    return [config["measure"]] if config.get("measure") else []


def result_dimension_names(config: dict, db: Session | None = None) -> list[str]:
    if config.get("indicatorType") == "derived" and db is not None:
        base_ids = config.get("baseIndicatorIds") or []
        first = db.get(Indicator, base_ids[0]) if base_ids else None
        if first:
            base_config = json.loads(first.config_json)
            names = [item.get("alias") or item["fieldName"] for item in base_config.get("dimensions") or []]
        else:
            names = []
    else:
        names = [item.get("alias") or item["fieldName"] for item in config.get("dimensions") or []]
    return [name for name in names if name]


def result_metric_names(config: dict) -> list[str]:
    if config.get("indicatorType") == "derived":
        names = [(config.get("derived") or {}).get("alias") or "衍生指标值"]
    else:
        names = []
        for measure in measures_of(config):
            alias = measure.get("alias") or measure["fieldName"]
            names.append(alias)
            names.extend(
                derivative_alias(alias, derivative)
                for derivative in measure.get("derivatives") or []
            )
    return [name for name in names if name]


def aggregate_function(value: object) -> str:
    function = str(value or "SUM").upper()
    if function not in {"SUM", "AVG", "MAX", "MIN", "COUNT"}:
        raise ValueError("不支持的聚合函数")
    return function


def measure_expression(item: dict, config: dict | None = None, main_model_id: str = "") -> str:
    field_name = str(item.get("fieldName") or "").strip()
    if not field_name:
        raise ValueError("度量字段不能为空")
    alias = alias_of_model(config or {}, str(item.get("modelId") or ""), main_model_id) if config else "a"
    return sql_field(field_name, alias)


def alias_of_model(config: dict, model_id: str, main_model_id: str) -> str:
    """根据 modelId 推导 SQL 表别名。

    主模型或 modelId 缺省 → 'a'；第 N 个 join 模型 → 'jN'。
    若 modelId 未匹配任何 join（配置漂移），兜底返回 'a'。
    """
    if not model_id or model_id == main_model_id:
        return "a"
    for idx, join in enumerate(config.get("joins") or [], start=1):
        if join.get("modelId") == model_id:
            return f"j{idx}"
    return "a"


def validate_field_sources(config: dict, main_model: DataModel, db: Session) -> None:
    """校验维度/度量/筛选字段声明的 modelId 都在主模型或 join 模型范围内，且字段确实存在。"""
    valid_model_ids = {main_model.id} | {j.get("modelId") for j in config.get("joins") or []}
    # 模型 id → 字段名集合（懒加载）
    field_cache: dict[str, set[str]] = {}

    def fields_of(mid: str) -> set[str]:
        if mid not in field_cache:
            if mid == main_model.id:
                field_cache[mid] = {f.field_name for f in main_model.fields}
            else:
                m = db.get(DataModel, mid)
                field_cache[mid] = {f.field_name for f in m.fields} if m else set()
        return field_cache[mid]

    for section in ("dimensions", "measures", "filters"):
        for item in config.get(section) or []:
            mid = str(item.get("modelId") or "")
            if mid and mid not in valid_model_ids:
                raise ValueError(f"字段“{item.get('fieldName')}”的来源模型未关联，请先在模型关系中添加")
            if mid and mid not in field_cache:
                # modelId 不在合法范围（已 raise），跳过；正常路径下 mid 已合法
                continue
            field_name = str(item.get("fieldName") or "")
            target_mid = mid or main_model.id
            if field_name and field_name not in fields_of(target_mid):
                raise ValueError(f"字段“{field_name}”不存在于来源模型中")


def model_join_sql(db: Session, model: DataModel, joins: list[dict]) -> str:
    join_sql = ""
    for idx, join in enumerate(joins, start=1):
        join_model = db.get(DataModel, join.get("modelId"))
        if not join_model:
            raise ValueError("关联模型不存在")
        alias = f"j{idx}"
        conditions = join.get("conditions") or []
        if not conditions:
            raise ValueError("模型关系必须包含关联字段")
        main_fields = {field.field_name for field in model.fields}
        joined_fields = {field.field_name for field in join_model.fields}
        if any(condition.get("leftField") not in main_fields or condition.get("rightField") not in joined_fields for condition in conditions):
            raise ValueError("模型关联字段不存在")
        on_sql = " AND ".join(f"{sql_field(condition['leftField'])} = {sql_field(condition['rightField'], alias)}" for condition in conditions)
        join_type = str(join.get("joinType") or "LEFT").upper()
        join_keyword = {"LEFT": "LEFT JOIN", "INNER": "INNER JOIN", "RIGHT": "RIGHT JOIN", "FULL": "FULL OUTER JOIN"}.get(join_type)
        if not join_keyword:
            raise ValueError("不支持的模型关联方式")
        join_sql += f"\n{join_keyword} {model_table_expr(join_model)} {alias} ON {on_sql}"
    return join_sql


def generate_derived_sql(db: Session, config: dict) -> str:
    base_ids = config.get("baseIndicatorIds") or []
    indicators = [db.get(Indicator, indicator_id) for indicator_id in base_ids]
    if not indicators or any(indicator is None for indicator in indicators):
        raise ValueError("衍生指标引用的基础指标不存在")

    base_configs = [json.loads(indicator.config_json) for indicator in indicators if indicator]
    frequencies = {base_config.get("schedule", {}).get("frequency") or "日" for base_config in base_configs}
    if len(frequencies) > 1:
        raise ValueError("基础指标频度不一致，无法组合")
    dimensions = base_configs[0].get("dimensions") or []
    dimension_aliases = [item.get("alias") or item["fieldName"] for item in dimensions]
    for base_config in base_configs[1:]:
        aliases = [item.get("alias") or item["fieldName"] for item in base_config.get("dimensions") or []]
        if aliases != dimension_aliases:
            raise ValueError("基础指标维度不一致，无法自动组合")

    metrics = []
    for base_config in base_configs:
        base_measures = measures_of(base_config)
        if not base_measures:
            raise ValueError("基础指标缺少度量")
        metrics.append(base_measures[0].get("alias") or base_measures[0]["fieldName"])

    rule = config.get("derived") or {}
    operator = rule.get("operator") or "copy"
    output_alias = rule.get("alias") or "衍生指标值"
    if operator != "copy" and len(indicators) < 2:
        raise ValueError("当前组合规则至少需要两个基础指标")

    ctes = ",\n".join(f"b{index} AS (\n{indicator.sql_text.rstrip().rstrip(';')}\n)" for index, indicator in enumerate(indicators, start=1) if indicator)
    select_dimensions = []
    for alias in dimension_aliases:
        candidates = [f"b{index}.{quote_alias(alias)}" for index in range(1, len(indicators) + 1)]
        expression = candidates[0] if len(candidates) == 1 else f"COALESCE({', '.join(candidates)})"
        select_dimensions.append(f"  {expression} AS {quote_alias(alias)}")

    metric_refs = [f"COALESCE(b{index}.{quote_alias(metric)}, 0)" for index, metric in enumerate(metrics, start=1)]
    if operator == "sum":
        expression = " + ".join(metric_refs)
    elif operator == "difference":
        expression = f"{metric_refs[0]} - {metric_refs[1]}"
    elif operator == "ratio":
        expression = f"CASE WHEN {metric_refs[1]} = 0 THEN NULL ELSE {metric_refs[0]} / {metric_refs[1]} END"
    else:
        expression = metric_refs[0]

    joins = ""
    for index in range(2, len(indicators) + 1):
        conditions = " AND ".join(f"b1.{quote_alias(alias)} = b{index}.{quote_alias(alias)}" for alias in dimension_aliases)
        joins += f"\nFULL OUTER JOIN b{index} ON {conditions or '1 = 1'}"
    select_sql = ",\n".join(select_dimensions + [f"  {expression} AS {quote_alias(output_alias)}"])
    return f"WITH {ctes}\nSELECT\n{select_sql}\nFROM b1{joins};"


def generate_indicator_sql(db: Session, config: dict) -> str:
    if config.get("indicatorType") == "derived":
        return generate_derived_sql(db, config)

    model_id = str(config.get("modelId") or "").strip()
    if not model_id:
        raise ValueError("请选择数据模型")
    model = db.get(DataModel, model_id)
    if not model:
        raise ValueError("模型不存在")

    # 校验维度/度量/筛选字段的来源模型合法性
    if config.get("joins"):
        validate_field_sources(config, model, db)

    raw_dims = config.get("dimensions") or []
    # 维度去重（按 modelId:fieldName），避免前端状态异常导致 SELECT/GROUP BY 同列多次出现
    seen_dim_keys: set[str] = set()
    dims: list[dict] = []
    for item in raw_dims:
        dim_key = f"{item.get('modelId') or ''}:{item.get('fieldName') or ''}"
        if not item.get("fieldName") or dim_key in seen_dim_keys:
            continue
        seen_dim_keys.add(dim_key)
        dims.append(item)
    measures = measures_of(config)
    if not dims:
        raise ValueError("指标必须至少包含一个维度")
    if not measures:
        raise ValueError("指标必须至少包含一个度量")
    requested_derivatives = {
        derivative
        for measure in measures
        for derivative in measure.get("derivatives") or []
    }
    unknown_derivatives = requested_derivatives.difference(DERIVATIVE_LABELS)
    if unknown_derivatives:
        raise ValueError(f"不支持的衍生度量：{', '.join(sorted(unknown_derivatives))}")
    if requested_derivatives and (
        model.source_type not in {"report", "custom_sql"}
        or model.biz_date_type != "balance"
        or not model.source_template
    ):
        raise ValueError("衍生度量仅适用于配置了业务日期参数的余额类报表模型")

    stored_dimensions = sum(dim.get("fieldName") != "DATA_DATE" for dim in dims)
    result_columns = stored_dimensions + len(result_metric_names(config))
    if result_columns > FIELD_COUNT:
        raise ValueError(f"维度+度量列数超过预留 {FIELD_COUNT} 列上限")

    select_dims = [f"  {sql_field(d['fieldName'], alias_of_model(config, str(d.get('modelId') or ''), model_id))} AS {quote_alias(d.get('alias') or d['fieldName'])}" for d in dims]
    group_by = [sql_field(d["fieldName"], alias_of_model(config, str(d.get("modelId") or ""), model_id)) for d in dims]
    select_measures = []
    for m in measures:
        field_expr = measure_expression(m, config, model_id)
        agg_func = str(m.get("aggFunc") or "SUM").upper()
        alias = m.get("alias") or m.get("fieldName") or "度量值"
        if agg_func == "NONE":
            select_measures.append(f"  {field_expr} AS {quote_alias(alias)}")
        else:
            select_measures.append(f"  {aggregate_function(agg_func)}({field_expr}) AS {quote_alias(alias)}")

    join_sql = model_join_sql(db, model, config.get("joins") or [])

    where_sql = ""
    filters = config.get("filters") or []
    if filters:
        # 合并主模型 + 所有 join 模型的字段类型映射，用于筛选字段校验
        field_types = {field.field_name: field.data_type for field in model.fields}
        for join in config.get("joins") or []:
            join_model = db.get(DataModel, join.get("modelId"))
            if join_model:
                field_types.update({f.field_name: f.data_type for f in join_model.fields})
        clauses = []
        for index, item in enumerate(filters):
            prefix = "" if index == 0 else f"{filter_join(item)} "
            clauses.append(f"  {prefix}({filter_sql(item, field_types, config, model_id)})")
        where_sql = "\nWHERE\n" + "\n".join(clauses)

    select_sql = ",\n".join(select_dims + select_measures)
    group_sql = ", ".join(group_by)
    base = f"SELECT\n{select_sql}\nFROM {model_table_expr(model)} a{join_sql}{where_sql}\nGROUP BY\n  {group_sql}"

    derivatives: list[str] = []
    date_alias = next((d.get("alias") or d["fieldName"] for d in dims if d["fieldName"] == "DATA_DATE"), None)
    order = f"ORDER BY agg.{quote_alias(date_alias)}" if date_alias else "ORDER BY 1"

    for measure in measures:
        alias = measure.get("alias") or measure["fieldName"]
        for der in measure.get("derivatives") or []:
            out = quote_alias(derivative_alias(alias, der))
            q = f"agg.{quote_alias(alias)}"
            if der == "cumulative":
                derivatives.append(f"  SUM({q}) OVER ({order} ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS {out}")
            elif der == "rank_desc":
                derivatives.append(f"  RANK() OVER (ORDER BY {q} DESC) AS {out}")
            elif der == "dod_delta":
                derivatives.append(f"  {q} - LAG({q}) OVER ({order}) AS {out}")
            elif der == "dod_growth":
                derivatives.append(f"  CASE WHEN LAG({q}) OVER ({order}) = 0 THEN NULL ELSE ({q} - LAG({q}) OVER ({order})) / LAG({q}) OVER ({order}) END AS {out}")
            elif der in DATE_BASED_DERIVATIVES:
                continue

    if derivatives:
        derivative_sql = ",\n".join(derivatives)
        sql_text = f"WITH agg AS (\n{base}\n)\nSELECT\n  agg.*,\n{derivative_sql}\nFROM agg;"
    else:
        sql_text = base + ";"
    return sql_text
