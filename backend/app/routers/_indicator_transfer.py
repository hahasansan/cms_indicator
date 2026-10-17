"""指标 JSON 导入导出（跨环境数据迁移）。

- 导出：把指标（含完整 config）序列化为 JSON 文件，模型按 code、分类按 name 记录。
- 导入：全量校验（模型/分类/重名/SQL 试生成），有任何错误则整体停止；全部通过才写入。
- 衍生指标（derived）第一版不支持自动迁移：预览标注 skip，导入时跳过。

原则：sql_text 不信任导出文件，导入时按目标库模型重新生成。
"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.entity.models import DataModel, Indicator, IndicatorCategory, IndicatorVersion
from app.routers.deps import build_indicator_sql
from app.routers.indicators import _next_indicator_code
from app.utils.common import new_id
from app.utils.database import get_db

router = APIRouter(tags=["指标迁移"])

FORMAT = "indicator-transfer"
VERSION = 1


class IndicatorExportIn(BaseModel):
    ids: list[str] = []


class IndicatorTransferFileIn(BaseModel):
    format: str = ""
    version: int = 0
    indicators: list[dict] = []


# ---------------------------------------------------------------------------
# 导出
# ---------------------------------------------------------------------------
@router.post("/indicators/export")
def export_indicators(payload: IndicatorExportIn, db: Session = Depends(get_db)) -> Response:
    query = db.query(Indicator)
    if payload.ids:
        query = query.filter(Indicator.id.in_(payload.ids))
    inds = query.order_by(Indicator.code).all()
    if not inds:
        raise HTTPException(400, "没有可导出的指标")

    models = {m.id: m for m in db.query(DataModel).all()}
    cats = {c.id: c for c in db.query(IndicatorCategory).all()}

    items: list[dict] = []
    errors: list[str] = []
    derived_count = 0
    for ind in inds:
        try:
            config = json.loads(ind.config_json)
        except Exception as exc:
            errors.append(f"{ind.code}（{ind.name}）：config 解析失败：{exc}")
            continue
        if (config.get("indicatorType") or "basic") == "derived":
            derived_count += 1
        model = models.get(ind.model_id) if ind.model_id else None
        cat = cats.get(ind.category_id)
        items.append({
            "code": ind.code,
            "name": ind.name,
            "categoryName": cat.name if cat else "",
            "modelCode": (model.code or "") if model else "",
            "periodType": ind.period_type or "point",
            "status": ind.status,
            "config": config,
            "sqlText": ind.sql_text,
        })
    if errors:
        raise HTTPException(400, "导出中止，以下指标数据异常，请先修复：\n" + "\n".join(errors))

    file = {
        "format": FORMAT,
        "version": VERSION,
        "exportedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "derivedCount": derived_count,
        "indicators": items,
    }
    content = json.dumps(file, ensure_ascii=False, indent=2)
    filename = f"indicators_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return Response(
        content=content,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# 校验（preview 与 import 共用，保证两边口径一致）
# ---------------------------------------------------------------------------
def _validate_transfer(db: Session, indicators: list[dict]) -> dict:
    models = {m.code: m for m in db.query(DataModel).all() if m.code}
    cats = {c.name: c for c in db.query(IndicatorCategory).all()}
    existing_names = {row[0] for row in db.query(Indicator.name).all()}

    items: list[dict] = []
    missing_models: set[str] = set()
    missing_categories: set[str] = set()
    error_count = 0
    skip_count = 0

    for idx, item in enumerate(indicators, start=1):
        name = str(item.get("name") or "").strip()
        model_code = str(item.get("modelCode") or "").strip()
        category_name = str(item.get("categoryName") or "").strip()
        errors: list[str] = []
        config = item.get("config")
        if not isinstance(config, dict):
            config = {}
            errors.append("缺少 config 配置")

        ind_type = str(config.get("indicatorType") or "basic")
        if not name:
            errors.append("缺少指标名称")

        if ind_type == "derived":
            skip_count += 1
            items.append({
                "index": idx, "code": str(item.get("code") or ""), "name": name,
                "modelCode": model_code, "categoryName": category_name,
                "status": "skip", "errors": ["衍生指标暂不支持导入，本次跳过"],
            })
            continue

        # 模型校验
        model = models.get(model_code) if model_code else None
        if not model_code:
            errors.append("缺少模型编码")
        elif model is None:
            errors.append(f"模型不存在：{model_code}")
            missing_models.add(model_code)

        # 分类校验（空 = 归入根分类）
        if category_name and category_name not in cats:
            errors.append(f"分类不存在：{category_name}")
            missing_categories.add(category_name)

        # JOIN 配置暂不支持自动迁移（join.modelId 为源环境 id，无法映射）
        if config.get("joins"):
            errors.append("含多表 JOIN 配置，暂不支持自动迁移")

        # 名称重复
        if name and name in existing_names:
            errors.append(f"目标库已存在同名指标：{name}")

        # SQL 试生成（用目标库模型 id 替换 config.modelId）
        if model is not None and config and not config.get("joins"):
            try:
                build_indicator_sql(db, {**config, "modelId": model.id})
            except Exception as exc:
                errors.append(f"SQL 生成失败：{exc}")

        status = "error" if errors else "ok"
        if status == "error":
            error_count += 1
        items.append({
            "index": idx, "code": str(item.get("code") or ""), "name": name,
            "modelCode": model_code, "categoryName": category_name,
            "status": status, "errors": errors,
        })

    ok_count = sum(1 for i in items if i["status"] == "ok")
    return {
        "summary": {"total": len(items), "ok": ok_count, "error": error_count, "skip": skip_count},
        "items": items,
        "missingModels": sorted(missing_models),
        "missingCategories": sorted(missing_categories),
    }


# ---------------------------------------------------------------------------
# 导入
# ---------------------------------------------------------------------------
def _parse_transfer_file(payload: IndicatorTransferFileIn) -> list[dict]:
    if payload.format != FORMAT:
        raise HTTPException(400, "文件格式不正确，请使用本系统导出的指标 JSON 文件")
    if not payload.indicators:
        raise HTTPException(400, "文件中没有指标数据")
    return payload.indicators


@router.post("/indicators/import/preview")
def import_indicators_preview(payload: IndicatorTransferFileIn, db: Session = Depends(get_db)) -> dict:
    indicators = _parse_transfer_file(payload)
    return _validate_transfer(db, indicators)


@router.post("/indicators/import")
def import_indicators(payload: IndicatorTransferFileIn, db: Session = Depends(get_db)) -> dict:
    indicators = _parse_transfer_file(payload)
    report = _validate_transfer(db, indicators)
    if report["summary"]["error"] > 0:
        # 有错误则整体停止，返回完整报告
        return {"blocked": True, **report}

    models = {m.code: m for m in db.query(DataModel).all() if m.code}
    cats = {c.name: c for c in db.query(IndicatorCategory).all()}

    created: list[dict] = []
    for item in indicators:
        config = dict(item.get("config") or {})
        if (config.get("indicatorType") or "basic") == "derived":
            continue
        model = models[str(item.get("modelCode") or "")]
        cat = cats.get(str(item.get("categoryName") or "").strip())
        config["modelId"] = model.id
        sql_text = build_indicator_sql(db, config)
        ind = Indicator(
            id=new_id("ind"),
            code=_next_indicator_code(db),
            name=str(item.get("name") or "").strip(),
            model_id=model.id,
            parent_id=None,
            category_id=cat.id if cat else "root",
            status=str(item.get("status") or "enabled"),
            period_type=str(item.get("periodType") or "point"),
            config_json=json.dumps(config, ensure_ascii=False),
            sql_text=sql_text,
        )
        db.add(ind)
        db.add(IndicatorVersion(indicator_id=ind.id, version=1, config_json=ind.config_json, sql_text=sql_text))
        created.append({"code": ind.code, "name": ind.name})
    db.commit()
    return {"blocked": False, "created": created, "skipped": report["summary"]["skip"]}
