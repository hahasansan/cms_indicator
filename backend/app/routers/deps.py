"""多个 router 共享的 HTTP 辅助函数（从 main.py 拆出，逻辑未改）。"""
from __future__ import annotations

import re

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.sql_engine import generate_indicator_sql


def quote_ident(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise HTTPException(400, "非法表名")
    return f'"{name}"'


def build_indicator_sql(db: Session, config: dict) -> str:
    try:
        return generate_indicator_sql(db, config)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def report_row(db: Session, reptid: str) -> tuple[str, str, str]:
    row = db.execute(text("SELECT REPTID, REPTNA, SQLTXT FROM RP_REPORT WHERE REPTID = :rid"), {"rid": reptid}).first()
    if not row:
        raise HTTPException(404, "报表不存在")
    return str(row[0]), str(row[1]), str(row[2] or "")
