from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url

if TYPE_CHECKING:
    from app.services.dameng import DamengConfig


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
LEGACY_SQLITE_PATH = DATA_DIR / "indicator_system_pro.db"

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
    database_mode: str
    database_url: URL
    dm_schema: str
    cors_origins: tuple[str, ...] = ("*",)

    @property
    def database_label(self) -> str:
        if self.database_mode == "local":
            return str(self.database_url.database)
        return f"{self.database_url.host}:{self.database_url.port}/{self.dm_schema}"

    @property
    def is_local(self) -> bool:
        return self.database_mode == "local"


def _cors_origins() -> tuple[str, ...]:
    raw = (os.getenv("CORS_ORIGINS") or "*").strip() or "*"
    return tuple(origin.strip() for origin in raw.split(",") if origin.strip()) or ("*",)


def load_settings() -> Settings:
    mode = (os.getenv("APP_DATABASE") or "local").strip().lower()
    if mode in {"sqlite", "sqlite3", "本地"}:
        mode = "local"
    if mode not in {"local", "dameng", "dm"}:
        raise RuntimeError("APP_DATABASE 只能配置为 local 或 dameng")

    if mode == "local":
        raw_path = (os.getenv("LOCAL_DATABASE_PATH") or "").strip()
        database_path = Path(raw_path) if raw_path else LEGACY_SQLITE_PATH
        if not database_path.is_absolute():
            database_path = (PROJECT_DIR / database_path).resolve()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        return Settings(
            database_mode="local",
            database_url=URL.create("sqlite", database=str(database_path)),
            dm_schema="",
            cors_origins=_cors_origins(),
        )

    raw_url = (os.getenv("DM_DATABASE_URL") or "").strip()
    if raw_url:
        url = make_url(raw_url)
        if url.get_backend_name() != "dm":
            raise RuntimeError("DM_DATABASE_URL 必须使用 dm 或 dm+dmPython 驱动")
        if not url.host or not url.username:
            raise RuntimeError("DM_DATABASE_URL 必须包含达梦主机和用户名")
        if url.password is None:
            raise RuntimeError("DM_DATABASE_URL 必须包含达梦数据库密码")
        schema = _schema(os.getenv("DM_SCHEMA") or url.database or url.username)
        return Settings(
            database_mode="dameng",
            database_url=url,
            dm_schema=schema,
            cors_origins=_cors_origins(),
        )

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
        database_mode="dameng",
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
