"""指标运行核心：run_indicator / run_batch_indicators。

从 main.py 拆出（纯移动，逻辑未改），供路由与定时调度共用。
"""
from __future__ import annotations

import calendar
import json
from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.config import get_dameng_config
from app.entity.models import DataModel, Indicator, JobRun
from app.entity.schemas import RunIn
from app.services.biz_date import resolve_biz_dates
from app.services.dameng import query_rows as dm_query_rows
from app.services.report_engine import resolve_report_for_date
from app.services.result_writer import build_field_map, rows_to_wide, save_field_map, write_results
from app.services.sql_engine import (
    DATE_BASED_DERIVATIVES,
    derivative_alias,
    generate_indicator_sql,
    measures_of,
    quote_alias,
    result_dimension_names,
    result_metric_names,
)
from app.utils.common import new_id

logger = get_logger("runner")


def _shift_months(value: date, months: int) -> date | None:
    month_index = value.year * 12 + value.month - 1 + months
    year, month_index = divmod(month_index, 12)
    month = month_index + 1
    if value.day > calendar.monthrange(year, month)[1]:
        return None
    return date(year, month, value.day)


def _quarter_start(value: date) -> date:
    return date(value.year, ((value.month - 1) // 3) * 3 + 1, 1)


def _period_dates(value: date, derivative: str) -> tuple[date, ...]:
    if derivative.startswith("month_"):
        start = value.replace(day=1)
    elif derivative.startswith("quarter_"):
        start = _quarter_start(value)
    else:
        start = value.replace(month=1, day=1)
    return tuple(start + timedelta(days=offset) for offset in range((value - start).days + 1))


def _date_derivative_target(value: date, derivative: str) -> date | None:
    if derivative.startswith("prev_day_"):
        return value - timedelta(days=1)
    if derivative.startswith("prev_month_"):
        return _shift_months(value, -1)
    if derivative.startswith("year_start_comparison_"):
        return value.replace(month=1, day=1)
    if derivative.startswith("prev_year_"):
        return _shift_months(value, -12)
    if derivative == "month_start_value":
        return value.replace(day=1)
    if derivative == "quarter_start_value":
        return _quarter_start(value)
    if derivative == "year_start_value":
        return value.replace(month=1, day=1)
    if derivative == "month_end_value":
        return value.replace(day=calendar.monthrange(value.year, value.month)[1])
    if derivative == "quarter_end_value":
        quarter_end_exclusive = _shift_months(_quarter_start(value), 3)
        return quarter_end_exclusive - timedelta(days=1) if quarter_end_exclusive else None
    if derivative == "year_end_value":
        return date(value.year, 12, 31)
    return None


def _build_balance_derivative_sql(
    db: Session,
    model: DataModel,
    config: dict,
    business_date: date,
) -> str:
    measures = measures_of(config)
    selected = [
        (measure, derivative)
        for measure in measures
        for derivative in measure.get("derivatives") or []
        if derivative in DATE_BASED_DERIVATIVES
    ]
    if not selected:
        return generate_indicator_sql(db, config)

    base_config = dict(config)
    base_config["measures"] = [
        {
            **measure,
            "derivatives": [
                derivative
                for derivative in measure.get("derivatives") or []
                if derivative not in DATE_BASED_DERIVATIVES
            ],
        }
        for measure in measures
    ]
    dates = {business_date}
    for _, derivative in selected:
        if derivative.endswith(("_cumulative", "_average")):
            dates.update(_period_dates(business_date, derivative))
        else:
            target = _date_derivative_target(business_date, derivative)
            if target:
                dates.add(target)

    source_template = model.source_template or ""

    def query_for(value: date) -> str:
        report_sql = resolve_report_for_date(
            source_template,
            {
                "type": model.biz_date_type,
                "field": model.biz_date_field,
                "start_param": model.biz_date_start_param,
                "end_param": model.biz_date_end_param,
            },
            {"single": value.strftime("%Y%m%d")},
        )
        model.source_sql = report_sql
        return generate_indicator_sql(db, base_config).strip().rstrip(";")

    original_source = model.source_sql
    try:
        snapshot_queries = {value: query_for(value) for value in sorted(dates)}
    finally:
        model.source_sql = original_source

    snapshots = [
        (
            f"SELECT TO_DATE('{value.isoformat()}', 'YYYY-MM-DD') AS \"__BIZ_DATE\", snapshot.* "
            f"FROM (\n{query}\n) snapshot"
        )
        for value, query in snapshot_queries.items()
    ]

    dimensions = [
        item.get("alias") or item["fieldName"]
        for item in config.get("dimensions") or []
        if item.get("fieldName") != "DATA_DATE"
    ]
    history_columns = [f'hist.{quote_alias(name)} AS {quote_alias(name)}' for name in dimensions]
    final_derivatives: list[str] = []
    reference_index = 0
    period_ranges = {
        "month": (business_date.replace(day=1), business_date),
        "quarter": (_quarter_start(business_date), business_date),
        "year": (business_date.replace(month=1, day=1), business_date),
    }
    reference_derivatives = {
        "prev_day_value", "prev_day_growth",
        "prev_month_value", "prev_month_growth",
        "year_start_comparison_value", "year_start_comparison_growth",
        "prev_year_value", "prev_year_growth",
        "month_start_value", "quarter_start_value", "year_start_value",
        "month_end_value", "quarter_end_value", "year_end_value",
    }
    for measure, derivative in selected:
        measure_alias = measure.get("alias") or measure["fieldName"]
        measure_column = f'hist.{quote_alias(measure_alias)}'
        output = quote_alias(derivative_alias(measure_alias, derivative))
        if derivative in reference_derivatives:
            reference_index += 1
            reference_alias = f"__DERIVATIVE_REF_{reference_index}"
            target = _date_derivative_target(business_date, derivative)
            if target:
                date_literal = f"TO_DATE('{target.isoformat()}', 'YYYY-MM-DD')"
                expression = (
                    f"MAX(CASE WHEN hist.\"__BIZ_DATE\" = {date_literal} "
                    f"THEN {measure_column} END)"
                )
            else:
                expression = "CAST(NULL AS NUMBER)"
            history_columns.append(f"  {expression} AS {quote_alias(reference_alias)}")
            reference_value = f"history_agg.{quote_alias(reference_alias)}"
            if derivative.endswith("_growth"):
                final_derivatives.append(
                    f"  CASE WHEN {reference_value} IS NULL OR {reference_value} = 0 "
                    f"THEN NULL ELSE (current_data.{quote_alias(measure_alias)} - {reference_value}) "
                    f"/ {reference_value} * 100 END AS {output}"
                )
            else:
                final_derivatives.append(f"  {reference_value} AS {output}")
            continue

        period = derivative.split("_", 1)[0]
        start, end = period_ranges[period]
        start_sql = f"TO_DATE('{start.isoformat()}', 'YYYY-MM-DD')"
        end_sql = f"TO_DATE('{end.isoformat()}', 'YYYY-MM-DD')"
        aggregate = "SUM" if derivative.endswith("_cumulative") else "AVG"
        history_columns.append(
            f"  {aggregate}(CASE WHEN hist.\"__BIZ_DATE\" BETWEEN {start_sql} AND {end_sql} "
            f"THEN {measure_column} END) AS {output}"
        )
        final_derivatives.append(f"  history_agg.{output} AS {output}")

    group_by = ", ".join(f'hist.{quote_alias(name)}' for name in dimensions)
    join_conditions = [
        f"(current_data.{quote_alias(name)} = history_agg.{quote_alias(name)} OR "
        f"(current_data.{quote_alias(name)} IS NULL AND history_agg.{quote_alias(name)} IS NULL))"
        for name in dimensions
    ]
    join_sql = " AND ".join(join_conditions) or "1 = 1"
    history_aggregate_sql = ",\n".join(history_columns)
    return (
        "WITH current_data AS (\n"
        f"{snapshot_queries[business_date]}\n"
        "), balance_snapshots AS (\n"
        + "\nUNION ALL\n".join(snapshots)
        + "), history_agg AS (\n"
        f"SELECT\n{history_aggregate_sql}\nFROM balance_snapshots hist"
        + (f"\nGROUP BY {group_by}" if group_by else "")
        + "\n)\nSELECT\n  current_data.*,\n"
        + ",\n".join(final_derivatives)
        + f"\nFROM current_data LEFT JOIN history_agg ON {join_sql};"
    )


def run_indicator(indicator_id: str, payload: RunIn, db: Session) -> dict:
    ind = db.get(Indicator, indicator_id)
    if not ind:
        raise HTTPException(404, "指标不存在")
    sql_text = ind.sql_text
    period_type = (ind.period_type or "point").lower()
    indicator_config = json.loads(ind.config_json)
    date_derivatives = {
        derivative
        for measure in measures_of(indicator_config)
        for derivative in measure.get("derivatives") or []
        if derivative in DATE_BASED_DERIVATIVES
    }
    model = db.get(DataModel, ind.model_id) if ind.model_id else None
    if date_derivatives and not payload.dateOption:
        raise HTTPException(400, "余额类衍生度量运行时必须指定业务日期")
    if date_derivatives and (
        not model
        or model.source_type not in {"report", "custom_sql"}
        or model.biz_date_type != "balance"
        or not model.source_template
    ):
        raise HTTPException(400, "衍生度量仅适用于配置了业务日期参数的余额类报表模型")
    biz_dates: dict[str, str] = resolve_biz_dates(payload.dateOption) if payload.dateOption else {}
    # 报表及自定义 SQL 模型：按业务日期选项代入模板参数
    if payload.dateOption and model:
        if model.source_type in {"report", "custom_sql"} and model.source_template:
            # 跑批前校验 biz_date 参数完整性：避免配错时报表 SQL 残留 :xxx 占位符
            if model.biz_date_type == "balance" and not model.biz_date_start_param:
                raise HTTPException(400, "余额类报表未配置业务日期参数，无法按日期跑批")
            if model.biz_date_type == "period" and not (model.biz_date_start_param and model.biz_date_end_param):
                raise HTTPException(400, "时段类报表未完整配置起止业务日期参数，无法按日期跑批")
            # 选项类型与指标模型类型不一致时兜底：余额类取 end 作为单日；时段类用 single 作起止
            if model.biz_date_type == "balance" and "single" not in biz_dates and biz_dates.get("end"):
                biz_dates = {"single": biz_dates["end"]}
            elif model.biz_date_type == "period" and "start" not in biz_dates and biz_dates.get("single"):
                biz_dates = {"start": biz_dates["single"], "end": biz_dates["single"]}
            report_biz_dates = {
                key: datetime.strptime(value, "%Y-%m-%d").strftime("%Y%m%d")
                for key, value in biz_dates.items()
            }
            resolved = resolve_report_for_date(
                model.source_template,
                {"type": model.biz_date_type, "field": model.biz_date_field, "start_param": model.biz_date_start_param, "end_param": model.biz_date_end_param},
                report_biz_dates,
            )
            if date_derivatives and not resolved:
                raise HTTPException(400, "无法按业务日期生成余额类衍生度量查询")
            if resolved:
                if date_derivatives:
                    if model.biz_date_type != "balance" or "single" not in biz_dates:
                        raise HTTPException(400, "余额类衍生度量必须使用单日业务日期参数")
                    business_date = datetime.strptime(biz_dates["single"], "%Y-%m-%d").date()
                    sql_text = _build_balance_derivative_sql(db, model, indicator_config, business_date)
                else:
                    original_source = model.source_sql
                    model.source_sql = resolved
                    try:
                        sql_text = generate_indicator_sql(db, indicator_config)
                    finally:
                        model.source_sql = original_source

    # 业务日期赋值（按 period_type）
    single_date = ""
    business_start_date = None
    business_end_date = None
    if period_type == "period":
        business_start_date = biz_dates.get("start") 
        business_end_date = biz_dates.get("end")
    else:
        single_date = biz_dates.get("single", "")

    run_id = new_id("run")
    job = JobRun(
        id=run_id,
        indicator_id=indicator_id,
        status="running",
        single_date=single_date,
        business_start_date=business_start_date,
        business_end_date=business_end_date,
        sql_text=sql_text,
    )
    db.add(job)
    db.commit()
    try:
        source = get_dameng_config()
        rows = dm_query_rows(source, sql_text)
        # DATA_DATE 维度存在 job_runs.single_date，不占 FIELD 列
        date_dimension = next(
            (item.get("alias") or item["fieldName"] for item in indicator_config.get("dimensions") or [] if item.get("fieldName") == "DATA_DATE"),
            None,
        )
        dimension_names = [d for d in result_dimension_names(indicator_config, db) if d != date_dimension]
        metric_names = result_metric_names(indicator_config)
        written = 0
        try:
            field_map = build_field_map(dimension_names, metric_names)
            wide_rows = rows_to_wide(rows, field_map)
            written = write_results(db, ind.code, run_id, wide_rows)
            # 保存 field_map 到指标表，供查询时前端读取
            save_field_map(db, indicator_id, field_map)
            logger.info("统一结果表写入 %s 行（指标 %s）", written, ind.code)
        except Exception as exc:
            db.rollback()
            raise RuntimeError(f"结果表写入失败：{exc}") from exc
        job.status = "success"
        job.row_count = written
        job.message = "运行成功"
        job.ended_at = datetime.now()
        db.commit()
        return {"runId": run_id, "status": "success", "rowCount": written, "rows": rows[:20], "sqlText": sql_text}
    except HTTPException as exc:
        db.rollback()
        failed_job = db.get(JobRun, run_id)
        failed_job.status = "failed"
        failed_job.message = str(exc.detail)
        failed_job.ended_at = datetime.now()
        db.commit()
        raise
    except Exception as exc:
        db.rollback()
        failed_job = db.get(JobRun, run_id)
        failed_job.status = "failed"
        failed_job.message = str(exc)
        failed_job.ended_at = datetime.now()
        db.commit()
        raise HTTPException(400, f"指标运行失败：{exc}") from exc


def run_batch_indicators(db: Session, scope: str, category_id: str, indicator_ids: list[str], date_option: dict | None) -> dict:
    """按范围取一批指标，逐个用业务日期选项运行写结果。供接口和定时调度共用。"""
    if scope == "all":
        indicators = db.query(Indicator).all()
    elif scope == "category":
        indicators = db.query(Indicator).filter(Indicator.category_id == category_id).all()
    else:
        ids = list(dict.fromkeys(indicator_ids))
        indicators = db.query(Indicator).filter(Indicator.id.in_(ids)).all() if ids else []
    if not indicators:
        return {"total": 0, "success": 0, "failed": 0, "details": []}
    details: list[dict] = []
    success = 0
    for ind in indicators:
        try:
            result = run_indicator(ind.id, RunIn(dateOption=date_option), db)
            details.append({"indicatorId": ind.id, "indicatorCode": ind.code, "status": "success", "rowCount": result["rowCount"]})
            success += 1
        except HTTPException as exc:
            details.append({"indicatorId": ind.id, "indicatorCode": ind.code, "status": "failed", "message": str(exc.detail)})
        except Exception as exc:
            details.append({"indicatorId": ind.id, "indicatorCode": ind.code, "status": "failed", "message": str(exc)})
    return {"total": len(indicators), "success": success, "failed": len(indicators) - success, "details": details}
