"""数据模型：列表、创建（报表导入 / 自定义SQL导入）、字段更新。"""
from __future__ import annotations

from fastapi import Depends, HTTPException, APIRouter, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import DataModel, ModelField
from app.routers._model_import import (
    build_model_from_sql,
    do_sql_preview,
    do_sql_resolve_preview,
)
from app.routers.reports import import_report_model
from app.schemas import FieldIn, ModelCreateIn, SqlTemplatePreviewIn, SqlResolvePreviewIn
from app.serializers import model_to_dict

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
    query = db.query(DataModel)
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
    rows = db.query(DataModel).order_by(DataModel.name).all()
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
    row = db.get(DataModel, model_id)
    if not row:
        raise HTTPException(404, "模型不存在")
    return model_to_dict(row)


@router.put("/models/{model_id}/fields/{field_name}")
def update_model_field(model_id: str, field_name: str, payload: FieldIn, db: Session = Depends(get_db)) -> dict:
    field = db.query(ModelField).filter(ModelField.model_id == model_id, ModelField.field_name == field_name).first()
    if not field:
        raise HTTPException(404, "字段不存在")
    field.alias = payload.alias
    field.role = payload.role
    field.unit = payload.unit or ""
    field.is_date = payload.isDate
    field.is_org = payload.isOrg
    field.filterable = payload.filterable
    field.dict_set_id = payload.dictSetId
    db.commit()
    return model_to_dict(db.get(DataModel, model_id))