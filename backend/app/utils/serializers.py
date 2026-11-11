"""序列化：把 ORM 行转成 API 响应 dict（全部 camelCase 输出，Phase 4 统一）。

从 main.py 拆出（纯移动，字段名暂保持原样，Phase 4 统一命名）。
"""
from __future__ import annotations

import json
from datetime import datetime

from app.entity.models import DataModel, Indicator, IndicatorCategory, Schedule


def clean_dict(row) -> dict:
    return {k: v for k, v in row.__dict__.items() if not k.startswith("_")}


def dt(value) -> str | None:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else None


def model_to_dict(model: DataModel) -> dict:
    return {
        "id": model.id,
        "code": model.code,
        "name": model.name,
        "module": model.module,
        "owner": model.owner,
        "description": model.description,
        "status": model.status,
        "table": model.table_name,
        "sourceType": model.source_type,
        "sourceSql": model.source_sql,
        "sourceRef": model.source_ref,
        "sourceTemplate": model.source_template,
        "bizDateType": model.biz_date_type,
        "bizDateField": model.biz_date_field,
        "bizDateStartParam": model.biz_date_start_param,
        "bizDateEndParam": model.biz_date_end_param,
        "createdAt": model.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "fields": [
            {
                "name": f.field_name,
                "alias": f.alias,
                "role": f.role,
                "dataType": f.data_type,
                "unit": f.unit,
                "isDate": f.is_date,
                "isOrg": f.is_org,
                "filterable": f.filterable,
                "dictSetId": f.dict_set_id,
                "dictSetName": f.dict_set.set_name if f.dict_set else None,
            }
            for f in model.fields
        ],
    }


def indicator_to_dict(ind: Indicator) -> dict:
    config = json.loads(ind.config_json)
    biz_date = config.get("bizDate") if isinstance(config.get("bizDate"), dict) else {}
    return {
        "id": ind.id,
        "code": ind.code,
        "name": ind.name,
        "modelId": ind.model_id or "",
        "parentId": ind.parent_id or "",
        "categoryId": ind.category_id,
        "status": ind.status,
        "favorite": ind.favorite,
        "periodType": ind.period_type,
        "bizDateType": biz_date.get("type") or "",
        "config": config,
        "sqlText": ind.sql_text,
        "createdAt": ind.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updatedAt": ind.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


def indicator_category_to_dict(category: IndicatorCategory) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "parentId": category.parent_id,
        "sortOrder": category.sort_order,
        "enabled": category.enabled,
        "createdAt": dt(category.created_at),
        "updatedAt": dt(category.updated_at),
    }


def schedule_to_dict(schedule: Schedule, indicator_name: str = "") -> dict:
    return {
        "id": schedule.id,
        "indicator_id": schedule.indicator_id,
        "indicator_name": indicator_name,
        "name": schedule.name,
        "frequency": schedule.frequency,
        "run_time": schedule.run_time,
        "enabled": schedule.enabled,
        "last_run_at": dt(schedule.last_run_at),
        "next_run_at": dt(schedule.next_run_at),
        "created_at": dt(schedule.created_at),
        "dateOption": json.loads(schedule.date_option) if schedule.date_option else None,
        "scope": schedule.scope,
        "categoryId": schedule.category_id,
    }
