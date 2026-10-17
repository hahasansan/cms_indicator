from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from sqlalchemy.engine import URL

if TYPE_CHECKING:
    from app.services.dameng import DamengConfig


BACKEND_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BACKEND_DIR / ".env")


def _required(value: str | None, name: str) -> str:
    result = (value or "").strip()
    if not result:
        raise RuntimeError(f"缺少达梦数据库配置 {name}，请在 backend/.env 中配置")
    return result


def _schema(value: str) -> str:
    result = value.strip().upper()
    if not re.fullmatch(r"[A-Z_][A-Z0-9_$#]*", result):
        raise RuntimeError("DM_SCHEMA 只能包含字母、数字、下划线、$ 或 #，且不能以数字开头")
    return result


@dataclass(frozen=True)
class Settings:
    database_url: URL
    dm_schema: str
    cors_origins: tuple[str, ...] = ("*",)

    @property
    def database_label(self) -> str:
        return f"{self.database_url.host}:{self.database_url.port}/{self.dm_schema}"


def _cors_origins() -> tuple[str, ...]:
    raw = (os.getenv("CORS_ORIGINS") or "*").strip() or "*"
    return tuple(origin.strip() for origin in raw.split(",") if origin.strip()) or ("*",)


def load_settings() -> Settings:
    host = _required(os.getenv("DM_HOST", "101.34.72.65"), "DM_HOST")
    username = _required(os.getenv("DM_USERNAME", "ZIJIN"), "DM_USERNAME")
    password = _required(os.getenv("DM_PASSWORD", "ZIJIN1234q"), "DM_PASSWORD")
    try:
        port = int(os.getenv("DM_PORT", "5232"))
    except ValueError as exc:
        raise RuntimeError("DM_PORT 必须是有效端口号") from exc
    if not 1 <= port <= 65535:
        raise RuntimeError("DM_PORT 必须在 1 到 65535 之间")

    schema = _schema(os.getenv("DM_SCHEMA") or username)
    url = URL.create(
        "dm+dmPython",
        username=username,
        password=password,
        host=host,
        port=port,
    )
    return Settings(
        database_url=url,
        dm_schema=schema,
        cors_origins=_cors_origins(),
    )


settings = load_settings()
DATABASE_URL = settings.database_url
DM_SCHEMA = settings.dm_schema


def get_dameng_config() -> "DamengConfig":
    """从 .env 中读取业务达梦数据库连接配置，返回 DamengConfig 对象。"""
    from app.services.dameng import DamengConfig

    host = (os.getenv("DM_BIZ_HOST") or "127.0.0.1").strip()
    port = int((os.getenv("DM_BIZ_PORT") or "5236").strip())
    username = (os.getenv("DM_BIZ_USERNAME") or "SYSDBA").strip()
    password = (os.getenv("DM_BIZ_PASSWORD") or "").strip()
    schema = (os.getenv("DM_BIZ_SCHEMA") or username).strip().upper()
    return DamengConfig(host=host, port=port, username=username, password=password, schema=schema)
