"""码值管理：分类 / 码值集 / 码值项 的 CRUD。

核心原则：码值项只停用不物理删除，保证历史指标配置永远可翻译。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.entity.models import DictCategory, DictItem, DictSet
from app.entity.schemas import DictCategoryIn, DictItemIn, DictSetIn
from app.utils.database import get_db

router = APIRouter(tags=["码值"])


# ============================================================
# 序列化
# ============================================================
def _category_to_dict(row: DictCategory, set_count: int | None = None) -> dict:
    return {
        "id": row.id,
        "categoryCode": row.category_code,
        "categoryName": row.category_name,
        "sort": row.sort,
        "remark": row.remark or "",
        "setCount": set_count if set_count is not None else 0,
        "createdAt": row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else "",
    }


def _set_to_dict(row: DictSet, item_count: int | None = None, ref_count: int = 0) -> dict:
    return {
        "id": row.id,
        "categoryId": row.category_id,
        "categoryCode": row.category.category_code if row.category else "",
        "categoryName": row.category.category_name if row.category else "",
        "setCode": row.set_code,
        "setName": row.set_name,
        "status": row.status,
        "remark": row.remark or "",
        "itemCount": item_count if item_count is not None else 0,
        "refCount": ref_count,
        "createdAt": row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else "",
    }


def _item_to_dict(row: DictItem) -> dict:
    return {
        "id": row.id,
        "setId": row.set_id,
        "setCode": row.set.set_code if row.set else "",
        "setName": row.set.set_name if row.set else "",
        "itemCode": row.item_code,
        "itemName": row.item_name,
        "sort": row.sort,
        "status": row.status,
        "createdAt": row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else "",
    }


# ============================================================
# 码值分类
# ============================================================
@router.get("/dict/categories")
def list_categories(
    keyword: str = "",
    db: Session = Depends(get_db),
) -> list[dict]:
    """列出全部分类（数量少，不分页），按 sort、id 排序。"""
    query = db.query(DictCategory)
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(DictCategory.category_code.ilike(kw) | DictCategory.category_name.ilike(kw))
    rows = query.order_by(DictCategory.sort, DictCategory.id).all()
    return [_category_to_dict(r, db.query(DictSet).filter(DictSet.category_id == r.id).count()) for r in rows]


@router.post("/dict/categories")
def create_category(payload: DictCategoryIn, db: Session = Depends(get_db)) -> dict:
    if not payload.categoryCode or not payload.categoryName:
        raise HTTPException(400, "分类编码和名称必填")
    if db.query(DictCategory).filter(DictCategory.category_code == payload.categoryCode).first():
        raise HTTPException(400, f"分类编码 {payload.categoryCode} 已存在")
    row = DictCategory(
        category_code=payload.categoryCode,
        category_name=payload.categoryName,
        sort=payload.sort,
        remark=payload.remark,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _category_to_dict(row, 0)


@router.put("/dict/categories/{category_id}")
def update_category(category_id: int, payload: DictCategoryIn, db: Session = Depends(get_db)) -> dict:
    row = db.get(DictCategory, category_id)
    if not row:
        raise HTTPException(404, "分类不存在")
    if db.query(DictCategory).filter(
        DictCategory.category_code == payload.categoryCode, DictCategory.id != category_id
    ).first():
        raise HTTPException(400, f"分类编码 {payload.categoryCode} 已存在")
    row.category_code = payload.categoryCode
    row.category_name = payload.categoryName
    row.sort = payload.sort
    row.remark = payload.remark
    db.commit()
    db.refresh(row)
    set_count = db.query(DictSet).filter(DictSet.category_id == row.id).count()
    return _category_to_dict(row, set_count)


@router.delete("/dict/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)) -> dict:
    row = db.get(DictCategory, category_id)
    if not row:
        raise HTTPException(404, "分类不存在")
    set_count = db.query(DictSet).filter(DictSet.category_id == category_id).count()
    if set_count > 0:
        raise HTTPException(400, f"该分类下存在 {set_count} 个码值集，无法删除")
    db.delete(row)
    db.commit()
    return {"ok": True}


# ============================================================
# 码值集
# ============================================================
@router.get("/dict/sets")
def list_sets(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=200),
    categoryId: int | None = None,
    keyword: str = "",
    status: str = "",
    db: Session = Depends(get_db),
) -> dict:
    """分页查询码值集。可按分类筛选；新绑定时前端按 status=enabled 过滤。"""
    query = db.query(DictSet)
    if categoryId is not None:
        query = query.filter(DictSet.category_id == categoryId)
    if status:
        query = query.filter(DictSet.status == status)
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(DictSet.set_code.ilike(kw) | DictSet.set_name.ilike(kw))
    total = query.count()
    rows = (
        query.order_by(DictSet.id.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
        .all()
    )
    items = []
    for r in rows:
        item_count = db.query(DictItem).filter(DictItem.set_id == r.id).count()
        # 引用计数本期返回 0（模型字段引用统计后续接入）
        items.append(_set_to_dict(r, item_count, 0))
    return {"items": items, "total": total, "page": page, "pageSize": pageSize}


@router.get("/dict/sets/options")
def list_sets_options(
    categoryId: int | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    """给下拉用：仅 enabled 码值集。"""
    query = db.query(DictSet).filter(DictSet.status == "enabled")
    if categoryId is not None:
        query = query.filter(DictSet.category_id == categoryId)
    rows = query.order_by(DictSet.set_name).all()
    return [{"id": r.id, "setCode": r.set_code, "setName": r.set_name, "categoryId": r.category_id} for r in rows]


@router.post("/dict/sets")
def create_set(payload: DictSetIn, db: Session = Depends(get_db)) -> dict:
    if not payload.setCode or not payload.setName:
        raise HTTPException(400, "码值集编码和名称必填")
    if db.query(DictSet).filter(DictSet.set_code == payload.setCode).first():
        raise HTTPException(400, f"码值集编码 {payload.setCode} 已存在")
    if not db.get(DictCategory, payload.categoryId):
        raise HTTPException(400, "所选分类不存在")
    row = DictSet(
        category_id=payload.categoryId,
        set_code=payload.setCode,
        set_name=payload.setName,
        status=payload.status or "enabled",
        remark=payload.remark,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _set_to_dict(row, 0, 0)


@router.put("/dict/sets/{set_id}")
def update_set(set_id: int, payload: DictSetIn, db: Session = Depends(get_db)) -> dict:
    row = db.get(DictSet, set_id)
    if not row:
        raise HTTPException(404, "码值集不存在")
    if db.query(DictSet).filter(
        DictSet.set_code == payload.setCode, DictSet.id != set_id
    ).first():
        raise HTTPException(400, f"码值集编码 {payload.setCode} 已存在")
    if not db.get(DictCategory, payload.categoryId):
        raise HTTPException(400, "所选分类不存在")
    row.category_id = payload.categoryId
    row.set_code = payload.setCode
    row.set_name = payload.setName
    row.status = payload.status or "enabled"
    row.remark = payload.remark
    db.commit()
    db.refresh(row)
    item_count = db.query(DictItem).filter(DictItem.set_id == row.id).count()
    return _set_to_dict(row, item_count, 0)


@router.delete("/dict/sets/{set_id}")
def delete_set(set_id: int, db: Session = Depends(get_db)) -> dict:
    """删除码值集。本期不校验模型字段引用（refCount 返回 0）。

    被指标条件引用的判断后续接入；当前直接物理删除码值集 + 级联码值项。
    """
    row = db.get(DictSet, set_id)
    if not row:
        raise HTTPException(404, "码值集不存在")
    db.delete(row)
    db.commit()
    return {"ok": True}


# ============================================================
# 码值项
# ============================================================
@router.get("/dict/items")
def list_items(
    setId: int = Query(..., description="所属码值集 ID"),
    onlyEnabled: int = Query(0, description="传 1 表示只返回启用状态的码值项"),
    db: Session = Depends(get_db),
) -> list[dict]:
    """列出码值集下码值项。

    默认返回全部（含已停用，便于历史配置翻译）；传 onlyEnabled=1 只返回启用项，用于新筛选下拉。
    """
    query = db.query(DictItem).filter(DictItem.set_id == setId)
    if onlyEnabled:
        query = query.filter(DictItem.status == "enabled")
    rows = query.order_by(DictItem.sort, DictItem.id).all()
    return [_item_to_dict(r) for r in rows]


@router.post("/dict/items")
def create_item(payload: DictItemIn, setId: int = Query(...), db: Session = Depends(get_db)) -> dict:
    if not payload.itemCode or not payload.itemName:
        raise HTTPException(400, "码值编码和业务名称必填")
    if not db.get(DictSet, setId):
        raise HTTPException(400, "所属码值集不存在")
    if db.query(DictItem).filter(
        DictItem.set_id == setId, DictItem.item_code == payload.itemCode
    ).first():
        raise HTTPException(400, f"码值编码 {payload.itemCode} 在该码值集内已存在")
    row = DictItem(
        set_id=setId,
        item_code=payload.itemCode,
        item_name=payload.itemName,
        sort=payload.sort,
        status=payload.status or "enabled",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _item_to_dict(row)


@router.put("/dict/items/{item_id}")
def update_item(item_id: int, payload: DictItemIn, db: Session = Depends(get_db)) -> dict:
    row = db.get(DictItem, item_id)
    if not row:
        raise HTTPException(404, "码值项不存在")
    if db.query(DictItem).filter(
        DictItem.set_id == row.set_id,
        DictItem.item_code == payload.itemCode,
        DictItem.id != item_id,
    ).first():
        raise HTTPException(400, f"码值编码 {payload.itemCode} 在该码值集内已存在")
    row.item_code = payload.itemCode
    row.item_name = payload.itemName
    row.sort = payload.sort
    row.status = payload.status or "enabled"
    db.commit()
    db.refresh(row)
    return _item_to_dict(row)


@router.delete("/dict/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)) -> dict:
    """码值项只能停用，不能物理删除（保证历史可翻译）。

    调用此接口即停用。指标条件引用检测后续接入。
    """
    row = db.get(DictItem, item_id)
    if not row:
        raise HTTPException(404, "码值项不存在")
    row.status = "disabled"
    db.commit()
    db.refresh(row)
    return _item_to_dict(row)


@router.put("/dict/items/{item_id}/status")
def toggle_item_status(item_id: int, payload: DictItemIn, db: Session = Depends(get_db)) -> dict:
    row = db.get(DictItem, item_id)
    if not row:
        raise HTTPException(404, "码值项不存在")
    row.status = payload.status or "enabled"
    db.commit()
    db.refresh(row)
    return _item_to_dict(row)
