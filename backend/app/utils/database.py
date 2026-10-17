from __future__ import annotations

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

"""达梦数据库引擎、会话和依赖注入。"""

from app.core.config import DATABASE_URL, DM_SCHEMA, settings

import dmSQLAlchemy  # noqa: F401 - registers the Dameng SQLAlchemy dialect

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)


@event.listens_for(engine, "connect")
def set_default_schema(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(f'SET SCHEMA "{DM_SCHEMA}"')
    finally:
        cursor.close()


class Base(DeclarativeBase):
    pass


def check_database_connection() -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise RuntimeError(
            f"无法连接达梦数据库 {settings.database_label}，请检查 backend/.env 配置"
        ) from exc


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
