"""指标：CRUD、收藏、复制、版本管理、单指标运行。"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import Depends, HTTPException, APIRouter, Query
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from app.entity.models import DataModel, Indicator, IndicatorCategory, IndicatorVersion
from app.routers.deps import build_indicator_sql
from app.entity.schemas import FavoriteIn, IndicatorCategoryIn, IndicatorIn, RunIn
from app.utils.database import get_db
from app.utils.serializers import indicator_category_to_dict, indicator_to_dict
from app.services import scheduler as sched
from app.services.runner import run_indicator
from app.utils.common import new_id

router = APIRouter(tags=["指标"])


def _next_indicator_code(db: Session) -> str:
    """从 app_sequences 取号（用后自增）。无并发锁，单用户工具够用。"""
    row = db.execute(text("SELECT next_value FROM app_sequences WHERE name = 'indicator_code'")).first()
    if row is None:
        db.execute(text("INSERT INTO app_sequences (name, next_value) VALUES ('indicator_code', 2)"))
        return "IND00001"
    next_value = int(row[0])
    db.execute(text("UPDATE app_sequences SET next_value = :v WHERE name = 'indicator_code'"), {"v": next_value + 1})
    return f"IND{next_value:05d}"


def _check_parent(db: Session, parent_id: str, forbid_self: str | None = None) -> None:
    if not parent_id:
        return
    if parent_id == forbid_self:
        raise HTTPException(400, "父指标不能选择自身")
    if not db.get(Indicator, parent_id):
        raise HTTPException(400, "父指标不存在")


@router.get("/indicators")
def list_indicators(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=200),
    keyword: str = "",
    status: str = "",
    modelId: str = "",
    categoryId: str = "",
    db: Session = Depends(get_db),
) -> dict:
    """分页查询指标列表，按更新时间倒序。keyword 下推到 SQL。"""
    query = db.query(Indicator)
    if status:
        query = query.filter(Indicator.status == status)
    if modelId:
        query = query.filter(Indicator.model_id == modelId)
    if categoryId:
        query = query.filter(Indicator.category_id == categoryId)
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(or_(
            Indicator.name.ilike(kw),
            Indicator.code.ilike(kw),
        ))
    total = query.count()
    rows = (
        query.order_by(Indicator.updated_at.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
        .all()
    )
    return {"items": [indicator_to_dict(row) for row in rows], "total": total, "page": page, "pageSize": pageSize}


@router.get("/indicators/options")
def list_indicators_options(db: Session = Depends(get_db)) -> list[dict]:
    """轻量指标选项（给下拉/统计/同表筛选用），不含 config/sqlText 等重字段。

    resultTable 从 config 解析，供 ImpactPage 同表筛选用。
    """
    rows = db.query(Indicator).order_by(Indicator.updated_at.desc()).all()
    result = []
    for row in rows:
        try:
            config = json.loads(row.config_json)
            rt = (config.get("schedule") or {}).get("resultTable") or "T_IND_RESULT_D"
        except Exception:
            rt = "T_IND_RESULT_D"
        result.append({
            "id": row.id,
            "code": row.code,
            "name": row.name,
            "modelId": row.model_id or "",
            "categoryId": row.category_id,
            "status": row.status,
            "favorite": row.favorite,
            "periodType": row.period_type,
            "parentId": row.parent_id or "",
            "resultTable": rt,
            "createdAt": row.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updatedAt": row.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return result


@router.get("/indicators/{indicator_id}")
def get_indicator(indicator_id: str, db: Session = Depends(get_db)) -> dict:
    """获取单个指标完整详情（含 config/sqlText）。"""
    row = db.get(Indicator, indicator_id)
    if not row:
        raise HTTPException(404, "指标不存在")
    return indicator_to_dict(row)


@router.post("/indicators")
def create_indicator(payload: IndicatorIn, db: Session = Depends(get_db)) -> dict:
    _check_parent(db, payload.parentId or "")
    code = _next_indicator_code(db)
    sql_text = build_indicator_sql(db, payload.config)
    model = db.get(DataModel, payload.modelId) if payload.modelId else None
    period_type = "period" if model and model.biz_date_type == "period" else "point"
    ind = Indicator(id=new_id("ind"), code=code, name=payload.name, model_id=payload.modelId or None, parent_id=payload.parentId or None, category_id=payload.categoryId, status=payload.status, period_type=period_type, config_json=json.dumps(payload.config, ensure_ascii=False), sql_text=sql_text)
    db.add(ind)
    db.add(IndicatorVersion(indicator_id=ind.id, version=1, config_json=ind.config_json, sql_text=sql_text))
    db.commit()
    return indicator_to_dict(ind)


@router.put("/indicators/{indicator_id}")
def update_indicator(indicator_id: str, payload: IndicatorIn, db: Session = Depends(get_db)) -> dict:
    ind = db.get(Indicator, indicator_id)
    if not ind:
        raise HTTPException(404, "指标不存在")
    parent_id = payload.parentId or None
    _check_parent(db, parent_id or "", forbid_self=indicator_id)
    ancestor = parent_id
    while ancestor:
        if ancestor == indicator_id:
            raise HTTPException(400, "父指标不能选择当前指标的下级指标")
        ancestor = db.get(Indicator, ancestor).parent_id if db.get(Indicator, ancestor) else None

    ind.name = payload.name
    ind.model_id = payload.modelId or None
    ind.parent_id = parent_id
    ind.status = payload.status
    ind.category_id = payload.categoryId
    model = db.get(DataModel, payload.modelId) if payload.modelId else None
    ind.period_type = "period" if model and model.biz_date_type == "period" else "point"
    ind.config_json = json.dumps(payload.config, ensure_ascii=False)
    ind.sql_text = build_indicator_sql(db, payload.config)
    ind.updated_at = datetime.now()
    version = (db.query(func.max(IndicatorVersion.version)).filter(IndicatorVersion.indicator_id == ind.id).scalar() or 0) + 1
    db.add(IndicatorVersion(indicator_id=ind.id, version=version, config_json=ind.config_json, sql_text=ind.sql_text))
    db.commit()
    return indicator_to_dict(ind)


@router.post("/indicators/{indicator_id}/copies")
def copy_indicator(indicator_id: str, db: Session = Depends(get_db)) -> dict:
    old = db.get(Indicator, indicator_id)
    if not old:
        raise HTTPException(404, "指标不存在")
    payload = IndicatorIn(name=f"{old.name} - 副本", modelId=old.model_id or "", parentId=old.parent_id, status="draft", categoryId=old.category_id, config=json.loads(old.config_json))
    return create_indicator(payload, db)


@router.put("/indicators/{indicator_id}/favorite")
def update_indicator_favorite(indicator_id: str, payload: FavoriteIn, db: Session = Depends(get_db)) -> dict:
    ind = db.get(Indicator, indicator_id)
    if not ind:
        raise HTTPException(404, "指标不存在")
    ind.favorite = payload.favorite
    ind.updated_at = datetime.now()
    db.commit()
    return indicator_to_dict(ind)


@router.delete("/indicators/{indicator_id}")
def delete_indicator(indicator_id: str, db: Session = Depends(get_db)) -> dict:
    ind = db.get(Indicator, indicator_id)
    if ind:
        for schedule in list(ind.schedules):
            sched.remove(schedule.id)
        db.delete(ind)
        db.commit()
    return {"ok": True}


@router.get("/indicators/{indicator_id}/versions")
def versions(indicator_id: str, db: Session = Depends(get_db)) -> list[dict]:
    ind = db.get(Indicator, indicator_id)
    if not ind:
        raise HTTPException(404, "指标不存在")
    if db.query(IndicatorVersion).filter(IndicatorVersion.indicator_id == indicator_id).count() == 0:
        db.add(IndicatorVersion(indicator_id=ind.id, version=1, config_json=ind.config_json, sql_text=ind.sql_text))
        db.commit()
    rows = db.query(IndicatorVersion).filter(IndicatorVersion.indicator_id == indicator_id).order_by(IndicatorVersion.version.desc()).all()
    return [{"id": r.id, "version": r.version, "config": json.loads(r.config_json), "sqlText": r.sql_text, "savedAt": r.saved_at.strftime("%Y-%m-%d %H:%M:%S")} for r in rows]


@router.post("/indicators/{indicator_id}/versions/{version_id}/restores")
def restore_version(indicator_id: str, version_id: int, db: Session = Depends(get_db)) -> dict:
    ind = db.get(Indicator, indicator_id)
    if not ind:
        raise HTTPException(404, "指标不存在")
    version = db.query(IndicatorVersion).filter(IndicatorVersion.indicator_id == indicator_id, IndicatorVersion.id == version_id).first()
    if not version:
        raise HTTPException(404, "版本不存在")
    ind.config_json = version.config_json
    ind.sql_text = version.sql_text
    ind.updated_at = datetime.now()
    new_version = (db.query(func.max(IndicatorVersion.version)).filter(IndicatorVersion.indicator_id == indicator_id).scalar() or 0) + 1
    db.add(IndicatorVersion(indicator_id=ind.id, version=new_version, config_json=ind.config_json, sql_text=ind.sql_text))
    db.commit()
    return indicator_to_dict(ind)


@router.post("/indicators/{indicator_id}/runs")
def run_indicator_route(indicator_id: str, payload: RunIn, db: Session = Depends(get_db)) -> dict:
    return run_indicator(indicator_id, payload, db)


@router.get("/indicator-categories")
def list_indicator_categories(db: Session = Depends(get_db)) -> list[dict]:
    
    rows = db.query(IndicatorCategory).order_by(IndicatorCategory.sort_order, IndicatorCategory.created_at).all()
    return [indicator_category_to_dict(row) for row in rows]


@router.post("/indicator-categories")
def create_indicator_category(payload: IndicatorCategoryIn, db: Session = Depends(get_db)) -> dict:
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "分类名称不能为空")
    parent_id = payload.parentId or "root"
    if parent_id != "root" and not db.get(IndicatorCategory, parent_id):
        raise HTTPException(400, "上级分类不存在")
    exists = db.query(IndicatorCategory).filter(IndicatorCategory.name == name, IndicatorCategory.parent_id == parent_id).first()
    if exists:
        raise HTTPException(400, "同级分类名称已存在")
    row = IndicatorCategory(id=new_id("cat"), name=name, parent_id=parent_id, sort_order=payload.sortOrder, enabled=payload.enabled)
    db.add(row)
    db.commit()
    return indicator_category_to_dict(row)


@router.put("/indicator-categories/{category_id}")
def update_indicator_category(category_id: str, payload: IndicatorCategoryIn, db: Session = Depends(get_db)) -> dict:
    row = db.get(IndicatorCategory, category_id)
    if not row:
        raise HTTPException(404, "指标分类不存在")
    if category_id == "root":
        raise HTTPException(400, "系统根分类不能修改")
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "分类名称不能为空")
    parent_id = payload.parentId or "root"
    if parent_id == category_id:
        raise HTTPException(400, "上级分类不能选择自身")
    exists = db.query(IndicatorCategory).filter(IndicatorCategory.name == name, IndicatorCategory.parent_id == parent_id, IndicatorCategory.id != category_id).first()
    if exists:
        raise HTTPException(400, "同级分类名称已存在")
    row.name = name
    row.parent_id = parent_id
    row.sort_order = payload.sortOrder
    row.enabled = payload.enabled
    row.updated_at = datetime.now()
    db.commit()
    return indicator_category_to_dict(row)


@router.delete("/indicator-categories/{category_id}")
def delete_indicator_category(category_id: str, db: Session = Depends(get_db)) -> dict:
    if category_id == "root":
        raise HTTPException(400, "系统根分类不能删除")
    row = db.get(IndicatorCategory, category_id)
    if not row:
        return {"ok": True}
    if db.query(IndicatorCategory).filter(IndicatorCategory.parent_id == category_id).first():
        raise HTTPException(400, "当前分类包含下级分类，不能删除")
    if db.query(Indicator).filter(Indicator.category_id == category_id).first():
        raise HTTPException(400, "当前分类已关联指标，请先调整指标分类")
    db.delete(row)
    db.commit()
    return {"ok": True}
