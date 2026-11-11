"""数据模型：列表、创建（报表导入 / 自定义SQL导入）、字段更新。"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import Depends, HTTPException, APIRouter, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.entity.models import DataModel, Indicator, IndicatorVersion, ModelField
from app.routers._model_import import (
    build_model_from_sql,
    do_sql_preview,
    do_sql_resolve_preview,
)
from app.routers.reports import import_report_model
from app.entity.schemas import FieldIn, ModelCreateIn, ModelSqlUpdateIn, SqlTemplatePreviewIn, SqlResolvePreviewIn
from app.services.deletion import soft_delete_indicator
from app.routers.deps import build_indicator_sql
from app.utils.database import get_db
from app.utils.serializers import model_to_dict

router = APIRouter(tags=["模型"])


@router.get("/models")
def list_models(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=200),
    keyword: str = "",
    module: str = "",
    db: Session = Depends(get_db),
) -> dict:
    """分页查询模型列表，按更新时间倒序。"""
    query = db.query(DataModel).filter(DataModel.deleted_at.is_(None))
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(or_(
            DataModel.name.ilike(kw),
            DataModel.code.ilike(kw),
            DataModel.table_name.ilike(kw),
            DataModel.owner.ilike(kw),
            DataModel.description.ilike(kw),
        ))
    if module:
        query = query.filter(DataModel.module == module)
    total = query.count()
    rows = (
        query.order_by(DataModel.created_at.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
        .all()
    )
    return {"items": [model_to_dict(row) for row in rows], "total": total, "page": page, "pageSize": pageSize}


@router.get("/models/options")
def list_models_options(db: Session = Depends(get_db)) -> list[dict]:
    """轻量模型选项（给下拉/名称展示用），不含 fields 等重字段。"""
    rows = db.query(DataModel).filter(DataModel.deleted_at.is_(None)).order_by(DataModel.name).all()
    return [
        {
            "id": row.id,
            "code": row.code,
            "name": row.name,
            "table": row.table_name,
            "module": row.module,
            "fields": [],
            "bizDateType": row.biz_date_type,
        }
        for row in rows
    ]


@router.post("/models")
def create_model(payload: ModelCreateIn, db: Session = Depends(get_db)) -> dict:
    if payload.reptid:
        # 路径 1：从报表导入
        return import_report_model(payload, db)
    if not payload.sqlText:
        raise HTTPException(400, "请填写自定义 SQL 模板或选择报表导入")
    # 路径 2：自定义 SQL 导入
    if not payload.code or not payload.name:
        raise HTTPException(400, "请填写模型编码和模型名称")
    if db.query(DataModel).filter(DataModel.code == payload.code).first():
        raise HTTPException(400, f"编码 {payload.code} 已存在")
    table_name = (payload.tableName or "").strip() or f"SQL_{payload.code.upper() or 'MODEL'}"
    # source_type 统一命名前缀避免与表名冲突
    safe_code = "".join(c for c in payload.code if c.isalnum() or c == "_").upper() or "CUSTOM"
    return build_model_from_sql(
        db,
        payload,
        payload.sqlText,
        code=payload.code,
        name=payload.name,
        module=payload.module or "自定义SQL",
        table_name=table_name,
        source_type="custom_sql",
        source_ref=None,
        source_template=payload.sqlText,
        titles=None,
    )


@router.post("/models/sql-preview")
def sql_preview(payload: SqlTemplatePreviewIn, db: Session = Depends(get_db)) -> dict:
    """自定义 SQL 模板的解析预览（自动识别业务日期 + DESCRIBE 输出字段）。"""
    import fastapi
    try:
        return do_sql_preview(db, payload.sqlText, payload)  # type: ignore[arg-type]
    except fastapi.HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"SQL 执行失败：{exc}") from exc


@router.post("/models/sql-resolve-preview")
def sql_resolve_preview(payload: SqlResolvePreviewIn, db: Session = Depends(get_db)) -> dict:
    """自定义 SQL 模板代入示例业务日期，返回替换后的 SQL。"""
    try:
        return do_sql_resolve_preview(db, payload.sqlText, payload)  # type: ignore[arg-type]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"SQL 替换失败：{exc}") from exc


@router.get("/models/{model_id}")
def get_model(model_id: str, db: Session = Depends(get_db)) -> dict:
    """获取单个模型完整详情（含 fields）。"""
    row = db.query(DataModel).filter(DataModel.id == model_id, DataModel.deleted_at.is_(None)).first()
    if not row:
        raise HTTPException(404, "模型不存在")
    return model_to_dict(row)


@router.put("/models/{model_id}/sql")
def update_custom_sql_model(model_id: str, payload: ModelSqlUpdateIn, db: Session = Depends(get_db)) -> dict:
    """更新自定义 SQL 模型模板，并同步 SQL 输出字段。"""
    model = db.query(DataModel).filter(
        DataModel.id == model_id,
        DataModel.deleted_at.is_(None),
    ).first()
    if not model:
        raise HTTPException(404, "模型不存在")
    if model.source_type != "custom_sql":
        raise HTTPException(400, "仅支持修改自定义 SQL 模型")
    if not payload.sqlText.strip():
        raise HTTPException(400, "SQL 模板不能为空")

    preview = do_sql_preview(db, payload.sqlText, payload)
    if not preview["fields"]:
        raise HTTPException(400, "SQL 输出字段为空，无法更新模型")
    biz_date = preview["bizDate"]
    current_fields = {field.field_name: field for field in model.fields}
    output_fields = {field["field_name"] for field in preview["fields"]}
    indicators = db.query(Indicator).filter(
        Indicator.deleted_at.is_(None),
    ).all()
    affected_indicators: list[Indicator] = []
    removed_referenced_fields: set[str] = set()
    for indicator in indicators:
        if indicator.model_id == model_id:
            config = json.loads(indicator.config_json)
            affected_indicators.append(indicator)
        else:
            try:
                config = json.loads(indicator.config_json)
            except (json.JSONDecodeError, TypeError):
                continue
        referenced_model_ids = {
            str(config.get("modelId") or ""),
            *(str(join.get("modelId") or "") for join in config.get("joins") or []),
        }
        if model_id in referenced_model_ids and indicator not in affected_indicators:
            affected_indicators.append(indicator)
        if indicator not in affected_indicators:
            continue
        for section in ("dimensions", "measures", "filters"):
            for item in config.get(section) or []:
                source_model_id = str(item.get("modelId") or config.get("modelId") or "")
                field_name = str(item.get("fieldName") or "")
                if source_model_id == model_id and field_name in current_fields and field_name not in output_fields:
                    removed_referenced_fields.add(field_name)
    if removed_referenced_fields:
        raise HTTPException(
            400,
            "SQL 移除了指标正在使用的字段，无法更新：" + "、".join(sorted(removed_referenced_fields)),
        )

    for field_data in preview["fields"]:
        field_name = field_data["field_name"]
        field = current_fields.pop(field_name, None)
        if field:
            field.data_type = field_data["data_type"]
            field.is_date = field_data["is_date"]
        else:
            model.fields.append(ModelField(
                model_id=model.id,
                field_name=field_name,
                alias=field_data["alias"],
                role=field_data["role"],
                data_type=field_data["data_type"],
                unit="",
                is_date=field_data["is_date"],
                is_org=False,
                filterable=True,
            ))
    for removed_field in current_fields.values():
        model.fields.remove(removed_field)

    model.source_template = payload.sqlText
    model.source_sql = preview["sqlText"]
    model.biz_date_type = biz_date["type"] if biz_date["type"] != "none" else None
    model.biz_date_field = biz_date["field"] or None
    model.biz_date_start_param = biz_date["start_param"] or None
    model.biz_date_end_param = biz_date["end_param"] or None
    db.flush()
    try:
        for indicator in affected_indicators:
            updated_sql = build_indicator_sql(db, json.loads(indicator.config_json))
            if updated_sql == indicator.sql_text:
                continue
            indicator.sql_text = updated_sql
            indicator.updated_at = datetime.now()
            version = (
                db.query(func.max(IndicatorVersion.version))
                .filter(IndicatorVersion.indicator_id == indicator.id)
                .scalar()
                or 0
            ) + 1
            db.add(IndicatorVersion(
                indicator_id=indicator.id,
                version=version,
                config_json=indicator.config_json,
                sql_text=updated_sql,
            ))
    except HTTPException:
        db.rollback()
        raise
    db.commit()
    return model_to_dict(model)


@router.put("/models/{model_id}/fields/{field_name}")
def update_model_field(model_id: str, field_name: str, payload: FieldIn, db: Session = Depends(get_db)) -> dict:
    model = db.query(DataModel).filter(DataModel.id == model_id, DataModel.deleted_at.is_(None)).first()
    if not model:
        raise HTTPException(404, "模型不存在")
    field = db.query(ModelField).filter(ModelField.model_id == model_id, ModelField.field_name == field_name).first()
    if not field:
        raise HTTPException(404, "字段不存在")
    alias = (payload.alias or "").strip()
    role = (payload.role or "").strip()
    if not alias:
        raise HTTPException(400, "字段业务名称不能为空")
    if not role:
        raise HTTPException(400, "字段角色不能为空")
    if role not in {"dimension", "measure", "normal"}:
        raise HTTPException(400, "字段角色只能是 dimension / measure / normal")
    field.alias = alias
    field.role = role
    field.unit = (payload.unit or "").strip() or None
    field.is_date = payload.isDate
    field.is_org = payload.isOrg
    field.filterable = payload.filterable
    field.dict_set_id = payload.dictSetId
    db.commit()
    return model_to_dict(db.get(DataModel, model_id))


@router.delete("/models/{model_id}")
def delete_model(model_id: str, db: Session = Depends(get_db)) -> dict:
    model = db.query(DataModel).filter(DataModel.id == model_id, DataModel.deleted_at.is_(None)).first()
    if not model:
        raise HTTPException(404, "模型不存在")
    model.deleted_at = datetime.now()
    indicators = db.query(Indicator).filter(Indicator.deleted_at.is_(None)).all()
    dependent_indicators = []
    for indicator in indicators:
        if indicator.model_id == model_id:
            dependent_indicators.append(indicator)
            continue
        try:
            config = json.loads(indicator.config_json)
        except (json.JSONDecodeError, TypeError):
            continue
        referenced_model_ids = {
            str(config.get("modelId") or ""),
            *(str(join.get("modelId") or "") for join in config.get("joins") or []),
        }
        if model_id in referenced_model_ids and indicator not in dependent_indicators:
            dependent_indicators.append(indicator)
    for indicator in dependent_indicators:
        soft_delete_indicator(indicator)
    db.commit()
    return {"ok": True, "deletedIndicators": len(dependent_indicators)}