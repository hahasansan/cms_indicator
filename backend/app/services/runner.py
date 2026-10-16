"""指标运行核心：run_indicator / run_batch_indicators。

从 main.py 拆出（纯移动，逻辑未改），供路由与定时调度共用。
"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.config import get_dameng_config
from app.models import DataModel, Indicator, JobRun
from app.schemas import RunIn
from app.services.biz_date import resolve_biz_dates
from app.services.dameng import query_rows as dm_query_rows
from app.services.report_engine import resolve_report_for_date
from app.services.result_writer import build_field_map, rows_to_wide, save_field_map, write_results
from app.services.sql_engine import generate_indicator_sql, result_dimension_names, result_metric_names
from app.utils import new_id

logger = get_logger("runner")


def run_indicator(indicator_id: str, payload: RunIn, db: Session) -> dict:
    ind = db.get(Indicator, indicator_id)
    if not ind:
        raise HTTPException(404, "指标不存在")
    sql_text = ind.sql_text
    period_type = (ind.period_type or "point").lower()
    biz_dates: dict[str, str] = resolve_biz_dates(payload.dateOption) if payload.dateOption else {}
    # 报表模型：按业务日期选项代入报表模板的日期参数
    if payload.dateOption and ind.model_id:
        model = db.get(DataModel, ind.model_id)
        if model and model.source_type == "report" and model.source_template:
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
            resolved = resolve_report_for_date(
                model.source_template,
                {"type": model.biz_date_type, "field": model.biz_date_field, "start_param": model.biz_date_start_param, "end_param": model.biz_date_end_param},
                biz_dates,
            )
            if resolved:
                # 报表模型按业务日期运行：直接跑原始报表 SQL 时输出列是大写原字段名，
                # 后续按中文别名映射会落空写 0 行；这里把按日期代入后的报表 SQL 作为子查询，
                # 重建带分组聚合的指标 SQL，输出列仍为中文别名，映射自然生效。
                original_source = model.source_sql
                model.source_sql = resolved
                try:
                    sql_text = generate_indicator_sql(db, json.loads(ind.config_json))
                finally:
                    model.source_sql = original_source

    # 业务日期赋值（按 period_type）
    if period_type == "period":
        business_start_date = biz_dates.get("start") 
        business_end_date = biz_dates.get("end")
    else:
        single_date = biz_dates.get("single")

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
        indicator_config = json.loads(ind.config_json)
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
