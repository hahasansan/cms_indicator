from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.engine import URL


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import LEGACY_SQLITE_PATH, settings  # noqa: E402
from app.db import Base, check_database_connection, engine  # noqa: E402
import app.models  # noqa: E402, F401 - registers all ORM tables


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将旧版 SQLite 系统数据迁移到达梦数据库")
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=LEGACY_SQLITE_PATH,
        help=f"旧 SQLite 文件，默认：{LEGACY_SQLITE_PATH}",
    )
    parser.add_argument("--dry-run", action="store_true", help="只检查源数据和达梦目标，不写入数据")
    return parser.parse_args()


def table_count(connection, table) -> int:
    return int(connection.execute(select(func.count()).select_from(table)).scalar_one())


def main() -> int:
    args = parse_args()
    sqlite_path = args.sqlite_path.resolve()
    if not sqlite_path.is_file():
        raise SystemExit(f"SQLite 文件不存在：{sqlite_path}")

    source_engine = create_engine(URL.create("sqlite", database=str(sqlite_path)))
    source_inspector = inspect(source_engine)
    tables = Base.metadata.sorted_tables
    missing = [table.name for table in tables if not source_inspector.has_table(table.name)]
    if missing:
        raise SystemExit(f"SQLite 缺少系统表：{', '.join(missing)}")

    check_database_connection()
    Base.metadata.create_all(bind=engine)

    with source_engine.connect() as source, engine.connect() as target:
        source_counts = {table.name: table_count(source, table) for table in tables}
        target_counts = {table.name: table_count(target, table) for table in tables}

    occupied = {name: count for name, count in target_counts.items() if count}
    print(f"SQLite：{sqlite_path}")
    print(f"达梦：{settings.database_label}")
    for table in tables:
        print(f"  {table.name}: SQLite={source_counts[table.name]}, 达梦={target_counts[table.name]}")

    if occupied:
        details = ", ".join(f"{name}={count}" for name, count in occupied.items())
        raise SystemExit(f"达梦目标表不是空表，为避免重复数据已停止迁移：{details}")
    if args.dry_run:
        print("检查通过，未写入数据。")
        return 0

    copied: dict[str, int] = {}
    with source_engine.connect() as source, engine.begin() as target:
        for table in tables:
            rows = [dict(row) for row in source.execute(select(table)).mappings()]
            if rows:
                target.execute(table.insert(), rows)
            copied[table.name] = len(rows)

        for table in tables:
            actual = table_count(target, table)
            expected = copied[table.name]
            if actual != expected:
                raise RuntimeError(f"{table.name} 迁移校验失败：期望 {expected}，实际 {actual}")

    print(f"迁移完成，共迁移 {sum(copied.values())} 条系统数据，原 SQLite 文件保持不变。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
