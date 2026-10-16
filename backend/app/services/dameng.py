from __future__ import annotations

import importlib
import re
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from fastapi import HTTPException


@dataclass
class DamengConfig:
    host: str
    port: int
    username: str
    password: str
    schema: str


# ── 以下函数已弃用（原用于把 DamengConfig 序列化/反序列化存入 DataSource 表）
# 保留函数签名以免外部调用方一次性全崩，但内部不再依赖 DataSource

def dm_driver():
    try:
        return importlib.import_module("dmPython")
    except ImportError as exc:
        raise HTTPException(400, "未安装达梦 Python 驱动 dmPython，请先安装达梦数据库客户端/驱动后再测试连接。") from exc


def validate_ident(name: str, label: str = "标识符") -> str:
    value = str(name or "").strip().upper()
    if not re.fullmatch(r"[A-Z_一-鿿#$][A-Z0-9_$#一-鿿]*", value):
        raise HTTPException(400, f"非法{label}")
    return value


def qualified_table(schema: str, table_name: str) -> str:
    return f'"{validate_ident(schema, "模式名")}"."{validate_ident(table_name, "表名")}"'


@contextmanager
def connect(config: DamengConfig) -> Iterator[Any]:
    dm = dm_driver()
    conn = dm.connect(
        user=config.username,
        password=config.password,
        server=config.host,
        port=int(config.port),
    )
    try:
        try:
            cur = conn.cursor()
            cur.execute(f'SET SCHEMA "{validate_ident(config.schema, "模式名")}"')
            cur.close()
        except Exception:
            pass
        yield conn
    finally:
        conn.close()


def test_connection(config: DamengConfig) -> dict:
    with connect(config) as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        row = cur.fetchone()
        cur.close()
    return {"ok": True, "message": f"达梦连接成功：{config.host}:{config.port}/{config.schema}", "value": row[0] if row else 1}


def list_tables(config: DamengConfig) -> list[dict]:
    schema = validate_ident(config.schema, "模式名")
    with connect(config) as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT TABLE_NAME FROM ALL_TABLES WHERE OWNER = '{schema}' ORDER BY TABLE_NAME")
        names = [str(row[0]) for row in cur.fetchall()]
        result: list[dict] = []
        for name in names:
            cur.execute(f"SELECT COUNT(*) FROM {qualified_table(schema, name)}")
            count = cur.fetchone()[0]
            result.append({"name": name, "rowCount": int(count)})
        cur.close()
        return result


def table_fields(config: DamengConfig, table_name: str) -> list[dict]:
    schema = validate_ident(config.schema, "模式名")
    table = validate_ident(table_name, "表名")
    with connect(config) as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT COLUMN_NAME, DATA_TYPE FROM ALL_TAB_COLUMNS "
            f"WHERE OWNER = '{schema}' AND TABLE_NAME = '{table}' ORDER BY COLUMN_ID"
        )
        rows = cur.fetchall()
        cur.close()
    return [{"name": str(row[0]), "dataType": str(row[1] or "VARCHAR")} for row in rows]


def sample_rows(config: DamengConfig, table_name: str, limit: int = 50) -> list[dict]:
    schema = validate_ident(config.schema, "模式名")
    with connect(config) as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {qualified_table(schema, table_name)} WHERE ROWNUM <= {int(limit)}")
        columns = [item[0] for item in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        cur.close()
        return rows


def query_rows(config: DamengConfig, sql_text: str) -> list[dict]:
    with connect(config) as conn:
        cur = conn.cursor()
        cur.execute(sql_text.rstrip().rstrip(";"))
        columns = [item[0] for item in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        cur.close()
        return rows


def describe_query(config: DamengConfig, sql_text: str) -> list[dict]:
    """执行查询并返回输出列的 [{name, dataType}]（dataType 归一为 NUMBER/DATE/VARCHAR）。"""
    from app.services.type_inference import dm_description_type_to_field
    with connect(config) as conn:
        cur = conn.cursor()
        cur.execute(sql_text.rstrip().rstrip(";"))
        columns = []
        for meta in cur.description or []:
            raw = getattr(meta[1], "__name__", None) or str(meta[1])
            columns.append({"name": str(meta[0]), "dataType": dm_description_type_to_field(raw)})
        cur.close()
        return columns


# business_source / indicator_source / active_dameng_source 已删除
# 所有达梦连接统一使用 get_dameng_config() 从配置文件读取
