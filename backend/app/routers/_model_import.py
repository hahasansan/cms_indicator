"""报表 / 自定义 SQL 导入为数据模型的公共内核。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_dameng_config
from app.entity.models import DataModel, ModelField
from app.entity.schemas import ModelCreateIn, ReportImportIn, ResolvePreviewIn
from app.services.dameng import describe_query as dm_describe_query
from app.services.report_engine import (
    detect_biz_date,
    extract_optional_param_fields,
    resolve_report_for_date,
)
from app.utils.common import new_id
from app.utils.database import SessionLocal
from app.utils.serializers import model_to_dict


def _extract_fields_from_titles(titles, output_map: dict[str, str]) -> list[dict]:
    """从 RP_TITLE 登记字段与 SQL 输出列交集生成模型字段列表（报表模式专用）。"""
    fields: list[dict] = []
    seen: set[str] = set()
    for fildcd, fildna in titles:
        fildcd_text = str(fildcd or "").strip()
        if not fildcd_text or fildcd_text in seen:
            continue
        dtype = output_map.get(fildcd_text.lower())
        if dtype is None:
            continue
        seen.add(fildcd_text)
        fields.append(
            {
                "field_name": fildcd_text,
                "alias": str(fildna or fildcd_text),
                "role": "measure" if dtype == "NUMBER" else "dimension",
                "data_type": dtype,
                "is_date": dtype == "DATE",
            }
        )
    return fields


def _extract_fields_from_columns(columns, output_map: dict[str, str]) -> list[dict]:
    """从 DESCRIBE 结果直接生成字段列表（自定义 SQL 模式专用，alias 默认同列名）。"""
    fields: list[dict] = []
    seen: set[str] = set()
    for col in columns:
        name = str(col.get("name") or "").strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        dtype = output_map.get(name.lower()) or col.get("dataType") or "VARCHAR"
        fields.append(
            {
                "field_name": name,
                "alias": name,
                "role": "measure" if dtype == "NUMBER" else "dimension",
                "data_type": dtype,
                "is_date": dtype == "DATE",
            }
        )
    return fields


def _resolve_biz_config(sql_text: str) -> tuple[dict, dict]:
    """解析业务日期配置（自动识别）。

    返回 (storage_cfg, biz_date_info)：
    - storage_cfg: type='none' 规范为 None，用于存储到 DataModel
    - biz_date_info: 保持 type 原值（'none'/'balance'/'period'），用于 resolve_report_for_date
    """
    detected = detect_biz_date(sql_text) or {}
    cfg = {"type": "none", "field": "", "start_param": "", "end_param": ""}
    cfg.update(detected)
    biz_date_info = {
        "type": cfg.get("type"),
        "field": cfg.get("field"),
        "start_param": cfg.get("start_param"),
        "end_param": cfg.get("end_param"),
    }
    storage_cfg = dict(cfg)
    if storage_cfg.get("type") == "none":
        storage_cfg = {"type": None, "field": "", "start_param": "", "end_param": ""}
    return storage_cfg, biz_date_info


def _sample_dates(biz_date_type: str | None, sample_date: str, sample_start: str, sample_end: str) -> dict:
    """根据业务日期类型构造示例日期。"""
    if biz_date_type == "balance":
        return {"single": sample_date}
    if biz_date_type == "period":
        return {"start": sample_start, "end": sample_end}
    return {}


def _build_all_fields(titles, columns, output_map: dict[str, str], sql_text: str, biz_date_info: dict) -> list[dict]:
    """合并字段：优先 titles（报表模式），其次 columns（自定义 SQL 模式），再追加可选块参数字段。"""
    if titles is not None:
        fields = _extract_fields_from_titles(titles, output_map)
    else:
        fields = _extract_fields_from_columns(columns, output_map)
    existing_names = {f["field_name"].lower() for f in fields}
    for of in extract_optional_param_fields(sql_text, biz_date_info):
        if of["field_name"].lower() not in existing_names:
            fields.append({
                "field_name": of["field_name"],
                "alias": of["field_name"],
                "role": "dimension",
                "data_type": "VARCHAR",
                "is_date": False,
            })
            existing_names.add(of["field_name"].lower())
    return fields


def build_model_from_sql(
    db: Session,
    payload: ModelCreateIn,
    sql_text: str,
    *,
    code: str,
    name: str,
    table_name: str,
    module: str,
    source_type: str,
    source_ref: str | None,
    source_template: str | None,
    titles=None,
) -> dict:
    """通用内核：根据 SQL 模板 + 元信息创建 DataModel 及 ModelFields。

    Args:
        db: SQLAlchemy Session
        payload: 创建入参（字段 override / sourceId / 示例日期 / code 覆盖 / name 覆盖 / owner 等）
        sql_text: 模板 SQL（带参数占位符）
        code / name / table_name / module / source_type / source_ref / source_template:
            直接填充 DataModel 对应字段（传入前报表或自定义 SQL 模式已按各自规则组装好）
        titles: 报表模式有值（list[tuple]，[(FILDCD, FILDNA), ...]），自定义 SQL 传 None
    """
    # 调用方明确传入 code/name/module 作为基线；仅当同名字段在 payload 非空且语义明确时允许覆盖
    if source_type != "report":
        # 自定义 SQL / 其他非报表模式：payload.code/name 为用户必填，但这里仍再同步一次（与前端 doImportSql 保持一致）
        if payload.code:
            code = payload.code
        if payload.name:
            name = payload.name
    owner = payload.owner or (name and "当前用户") or "当前用户"
    description = payload.description or ""

    storage_cfg, biz_date_info = _resolve_biz_config(sql_text)
    sample_dates = _sample_dates(biz_date_info.get("type"), payload.sampleDate, payload.sampleStartDate, payload.sampleEndDate)
    resolved = resolve_report_for_date(sql_text, biz_date_info, sample_dates)
    source = get_dameng_config()
    try:
        columns = dm_describe_query(source, resolved)
    except Exception as exc:  # 让调用方可以捕获并包装错误消息；底层已 raise HTTPException 会透传
        raise
    output_map = {col["name"].lower(): col["dataType"] for col in columns}
    auto_fields = _build_all_fields(titles, columns, output_map, sql_text, biz_date_info)
    if not auto_fields:
        from fastapi import HTTPException
        raise HTTPException(400, "SQL 输出字段为空，无法导入")

    field_overrides = {f.field_name: f for f in payload.fields} if payload.fields else {}
    final_fields: list[dict] = []
    for f in auto_fields:
        override = field_overrides.get(f["field_name"])
        if override:
            final_fields.append({
                "field_name": f["field_name"],
                "alias": override.alias or f["alias"],
                "role": override.role or f["role"],
                "data_type": override.data_type or f["data_type"],
                "is_date": override.is_date if override.is_date is not None else f["is_date"],
                "is_org": override.is_org,
                "filterable": override.filterable if override.filterable is not None else True,
            })
        else:
            final_fields.append({**f, "is_org": False, "filterable": True})

    model = DataModel(
        id=new_id("mdl"),
        code=code,
        name=name,
        module=module,
        table_name=table_name,
        source_type=source_type,
        source_sql=resolved,
        source_ref=source_ref,
        source_template=source_template,
        biz_date_type=storage_cfg.get("type"),
        biz_date_field=storage_cfg.get("field") or None,
        biz_date_start_param=storage_cfg.get("start_param") or None,
        biz_date_end_param=storage_cfg.get("end_param") or None,
        owner=owner,
        description=description,
    )
    db.add(model)
    db.flush()
    for f in final_fields:
        db.add(
            ModelField(
                model_id=model.id,
                field_name=f["field_name"],
                alias=f["alias"],
                role=f["role"],
                data_type=f["data_type"],
                is_date=f["is_date"],
                is_org=f["is_org"],
                filterable=f["filterable"],
            )
        )
    db.commit()
    return model_to_dict(model)


def do_sql_preview(db: Session, sql_text: str, payload: ReportImportIn) -> dict:
    """代入业务日期示例值执行 DESCRIBE，返回字段列表 + 识别结果（支持自定义 SQL）。"""
    _, biz_date_info = _resolve_biz_config(sql_text)
    sample_dates = _sample_dates(biz_date_info.get("type"), payload.sampleDate, payload.sampleStartDate, payload.sampleEndDate)
    resolved = resolve_report_for_date(sql_text, biz_date_info, sample_dates)
    source = get_dameng_config()
    try:
        columns = dm_describe_query(source, resolved)
    except Exception as exc:
        raise
    output_map = {col["name"].lower(): col["dataType"] for col in columns}
    # 自定义 SQL 预览：titles=None，直接从 columns 取
    fields = _build_all_fields(None, columns, output_map, sql_text, biz_date_info)
    return {
        "templateSql": sql_text,
        "sqlText": resolved,
        "columns": columns,
        "bizDate": biz_date_info,
        "fields": fields,
    }


def do_sql_resolve_preview(db: Session, sql_text: str, payload: ResolvePreviewIn) -> dict:
    """按用户手动指定的业务日期参数替换，返回替换后的 SQL（支持自定义 SQL）。"""
    biz_date_info = {
        "type": payload.bizDateType,
        "field": payload.bizDateField,
        "start_param": payload.bizDateStartParam,
        "end_param": payload.bizDateEndParam,
    }
    sample_dates = _sample_dates(payload.bizDateType, payload.sampleDate, payload.sampleStartDate, payload.sampleEndDate)
    resolved_sql = resolve_report_for_date(sql_text, biz_date_info, sample_dates)
    return {"sqlText": resolved_sql, "templateSql": sql_text}
