"""CRUD for reusable measure formula templates."""
from __future__ import annotations

import json
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.entity.models import Indicator, MeasureFunction
from app.entity.schemas import MeasureFunctionIn
from app.services.measure_formula import formula_parameter_count
from app.utils.common import new_id
from app.utils.database import get_db


router = APIRouter(tags=["度量公式"])


def _parse_parameters(raw: str | None, count: int) -> list[str]:
    """把库里保存的操作数含义还原为与占位符数量一致的列表。"""
    try:
        values = json.loads(raw) if raw else []
    except (ValueError, TypeError):
        values = []
    if not isinstance(values, list):
        values = []
    result = [str(item or "").strip() for item in values][:count]
    return result + [""] * (count - len(result))


def _dump_parameters(values: list[str] | None, count: int) -> str | None:
    """校验并序列化操作数含义；全部为空时不写入数据库（达梦空字符串即 NULL）。"""
    items = [str(item or "").strip() for item in (values or [])][:count]
    items += [""] * (count - len(items))
    return json.dumps(items, ensure_ascii=False) if any(items) else None


def _function_to_dict(row: MeasureFunction) -> dict:
    count = formula_parameter_count(row.formula)
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "formula": row.formula,
        "description": row.description,
        "parameterCount": count,
        "parameters": _parse_parameters(row.parameters, count),
        "createdAt": row.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updatedAt": row.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _validated_values(payload: MeasureFunctionIn) -> tuple[str, str, str, str, int]:
    code = payload.code.strip().upper()
    name = payload.name.strip()
    formula = payload.formula.strip()
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", code):
        raise HTTPException(400, "函数编码需为 2-64 位大写字母、数字或下划线，且以字母开头")
    if not name:
        raise HTTPException(400, "函数名称不能为空")
    try:
        count = formula_parameter_count(formula)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if payload.parameters is not None and len(payload.parameters) > count:
        raise HTTPException(400, f"该公式只有 {count} 个操作数，操作数含义不能超过 {count} 项")
    return code, name, formula, payload.description.strip() or None, count


@router.get("/measure-functions")
def list_measure_functions(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(MeasureFunction).order_by(MeasureFunction.name, MeasureFunction.code).all()
    return [_function_to_dict(row) for row in rows]


@router.post("/measure-functions")
def create_measure_function(payload: MeasureFunctionIn, db: Session = Depends(get_db)) -> dict:
    code, name, formula, description, count = _validated_values(payload)
    if db.query(MeasureFunction).filter(MeasureFunction.code == code).first():
        raise HTTPException(400, f"函数编码 {code} 已存在")
    row = MeasureFunction(
        id=new_id("mfn"),
        code=code,
        name=name,
        formula=formula,
        description=description,
        parameters=_dump_parameters(payload.parameters, count),
    )
    db.add(row)
    db.commit()
    return _function_to_dict(row)


@router.put("/measure-functions/{function_id}")
def update_measure_function(function_id: str, payload: MeasureFunctionIn, db: Session = Depends(get_db)) -> dict:
    row = db.get(MeasureFunction, function_id)
    if not row:
        raise HTTPException(404, "度量公式不存在")
    code, name, formula, description, count = _validated_values(payload)
    duplicate = db.query(MeasureFunction).filter(
        MeasureFunction.code == code,
        MeasureFunction.id != function_id,
    ).first()
    if duplicate:
        raise HTTPException(400, f"函数编码 {code} 已存在")
    row.code = code
    row.name = name
    row.formula = formula
    row.description = description
    row.parameters = _dump_parameters(payload.parameters, count)
    row.updated_at = datetime.now()
    db.commit()
    return _function_to_dict(row)


@router.delete("/measure-functions/{function_id}")
def delete_measure_function(function_id: str, db: Session = Depends(get_db)) -> dict:
    row = db.get(MeasureFunction, function_id)
    if not row:
        raise HTTPException(404, "度量公式不存在")
    for indicator in db.query(Indicator).filter(Indicator.deleted_at.is_(None)).all():
        try:
            config = json.loads(indicator.config_json)
        except (ValueError, TypeError):
            continue
        configured = config.get("measures")
        measures = configured if isinstance(configured, list) else ([config["measure"]] if config.get("measure") else [])
        if any(
            isinstance(measure, dict) and measure.get("functionId") == function_id
            for measure in measures
        ):
            raise HTTPException(400, "该公式已被指标使用，不能删除")
    db.delete(row)
    db.commit()
    return {"ok": True}
