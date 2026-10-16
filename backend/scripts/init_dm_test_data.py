from __future__ import annotations

from datetime import date

import dmPython


HOST = "127.0.0.1"
PORT = 5236
USERNAME = "SYSDBA"
PASSWORD = "Zijin@12345"


TABLE_DEFINITIONS = {
    "DIM_ORG": """
        CREATE TABLE DIM_ORG (
            ORG_ID VARCHAR(32) NOT NULL,
            ORG_NAME VARCHAR(128) NOT NULL,
            ORG_LEVEL VARCHAR(32),
            PARENT_ORG_ID VARCHAR(32),
            STATUS VARCHAR(16),
            CONSTRAINT PK_DIM_ORG PRIMARY KEY (ORG_ID)
        )
    """,
    "DWD_MARKET_RATE_D": """
        CREATE TABLE DWD_MARKET_RATE_D (
            ID INTEGER NOT NULL,
            DATA_DATE DATE NOT NULL,
            PRODUCT_CODE VARCHAR(32) NOT NULL,
            PRODUCT_NAME VARCHAR(128) NOT NULL,
            TENOR VARCHAR(16),
            HIGH_PRICE DECIMAL(18, 6),
            LOW_PRICE DECIMAL(18, 6),
            CLOSE_PRICE DECIMAL(18, 6),
            PREV_DAY_CHANGE DECIMAL(18, 6),
            SOURCE_STATUS VARCHAR(16),
            CONSTRAINT PK_DWD_MARKET_RATE_D PRIMARY KEY (ID)
        )
    """,
    "DWD_BOND_POSITION_D": """
        CREATE TABLE DWD_BOND_POSITION_D (
            ID INTEGER NOT NULL,
            DATA_DATE DATE NOT NULL,
            ORG_ID VARCHAR(32) NOT NULL,
            BOND_CODE VARCHAR(32) NOT NULL,
            BOND_NAME VARCHAR(128) NOT NULL,
            BOND_TYPE VARCHAR(32),
            BOND_RATING VARCHAR(16),
            REMAIN_TERM DECIMAL(12, 4),
            FACE_VALUE DECIMAL(18, 2),
            MARKET_VALUE DECIMAL(18, 2),
            COST_VALUE DECIMAL(18, 2),
            YTM DECIMAL(12, 6),
            HOLD_STATUS VARCHAR(16),
            CONSTRAINT PK_DWD_BOND_POSITION_D PRIMARY KEY (ID)
        )
    """,
    "DWD_FUND_TRADE_D": """
        CREATE TABLE DWD_FUND_TRADE_D (
            ID INTEGER NOT NULL,
            DATA_DATE DATE NOT NULL,
            ORG_ID VARCHAR(32) NOT NULL,
            PRODUCT_TYPE VARCHAR(32),
            CURRENCY VARCHAR(16),
            TRADE_DIRECTION VARCHAR(16),
            COUNTERPARTY VARCHAR(128),
            TRADE_AMOUNT DECIMAL(18, 2),
            TRADE_RATE DECIMAL(12, 6),
            TRADE_COUNT INTEGER,
            CONSTRAINT PK_DWD_FUND_TRADE_D PRIMARY KEY (ID)
        )
    """,
    "DWD_CAPITAL_BALANCE_D": """
        CREATE TABLE DWD_CAPITAL_BALANCE_D (
            ID INTEGER NOT NULL,
            DATA_DATE DATE NOT NULL,
            ORG_ID VARCHAR(32) NOT NULL,
            ACCOUNT_TYPE VARCHAR(32),
            CURRENCY VARCHAR(16),
            BALANCE DECIMAL(18, 2),
            AVAILABLE_AMOUNT DECIMAL(18, 2),
            FROZEN_AMOUNT DECIMAL(18, 2),
            STATUS VARCHAR(16),
            CONSTRAINT PK_DWD_CAPITAL_BALANCE_D PRIMARY KEY (ID)
        )
    """,
}


ROWS = {
    "DIM_ORG": [
        ("ORG001", "总行资金部", "总行", "", "启用"),
        ("ORG002", "上海分行", "分行", "ORG001", "启用"),
        ("ORG003", "深圳分行", "分行", "ORG001", "启用"),
    ],
    "DWD_MARKET_RATE_D": [
        (1, date(2026, 7, 1), "CN10YGB", "中国10Y国开债", "10Y", 3.590000, 3.572500, 3.572700, -1.480000, "有效"),
        (2, date(2026, 7, 1), "CN10YGB", "中国10Y国债", "10Y", 3.190000, 3.170000, 3.170000, -0.175000, "有效"),
        (3, date(2026, 7, 1), "US10Y", "美国10Y国债", "10Y", 1.938200, 1.892500, 1.929400, 1.230000, "有效"),
        (4, date(2026, 7, 1), "DE10Y", "德国10Y国债", "10Y", -0.239000, -0.271000, -0.242000, 1.000000, "有效"),
        (5, date(2026, 7, 1), "JP10Y", "日本10Y国债", "10Y", 0.019000, 0.007000, 0.016000, 0.200000, "有效"),
        (6, date(2026, 7, 2), "CN10YGB", "中国10Y国开债", "10Y", 3.600000, 3.580000, 3.591000, 0.018300, "有效"),
        (7, date(2026, 7, 2), "CN10YGB", "中国10Y国债", "10Y", 3.200000, 3.175000, 3.185000, 0.015000, "有效"),
        (8, date(2026, 7, 2), "US10Y", "美国10Y国债", "10Y", 1.950000, 1.900000, 1.935000, 0.005600, "有效"),
        (9, date(2026, 7, 2), "DE10Y", "德国10Y国债", "10Y", -0.230000, -0.260000, -0.238000, 0.004000, "有效"),
        (10, date(2026, 7, 2), "JP10Y", "日本10Y国债", "10Y", 0.021000, 0.008000, 0.018000, 0.002000, "有效"),
    ],
    "DWD_BOND_POSITION_D": [
        (1, date(2026, 7, 1), "ORG001", "BOND001", "2025政策性金融债", "政策性金融债", "AAA", 8.25, 10000000.00, 10025000.00, 9980000.00, 2.315000, "持有"),
        (2, date(2026, 7, 1), "ORG002", "BOND002", "2024国债", "国债", "AAA", 6.80, 8000000.00, 8032000.00, 7995000.00, 2.080000, "持有"),
        (3, date(2026, 7, 2), "ORG001", "BOND001", "2025政策性金融债", "政策性金融债", "AAA", 8.24, 10000000.00, 10042000.00, 9980000.00, 2.290000, "持有"),
        (4, date(2026, 7, 2), "ORG003", "BOND003", "2023地方政府债", "地方政府债", "AAA", 4.60, 5000000.00, 5011000.00, 4990000.00, 2.460000, "持有"),
    ],
    "DWD_FUND_TRADE_D": [
        (1, date(2026, 7, 1), "ORG001", "同业存单", "CNY", "买入", "测试银行A", 30000000.00, 1.850000, 1),
        (2, date(2026, 7, 1), "ORG002", "质押式回购", "CNY", "卖出", "测试银行B", 18000000.00, 1.720000, 2),
        (3, date(2026, 7, 2), "ORG001", "同业存单", "CNY", "买入", "测试银行C", 25000000.00, 1.830000, 1),
        (4, date(2026, 7, 2), "ORG003", "质押式回购", "CNY", "买入", "测试银行A", 12000000.00, 1.680000, 1),
    ],
    "DWD_CAPITAL_BALANCE_D": [
        (1, date(2026, 7, 1), "ORG001", "结算备付金", "CNY", 85000000.00, 80000000.00, 5000000.00, "正常"),
        (2, date(2026, 7, 1), "ORG002", "存放同业", "CNY", 42000000.00, 42000000.00, 0.00, "正常"),
        (3, date(2026, 7, 2), "ORG001", "结算备付金", "CNY", 91000000.00, 86000000.00, 5000000.00, "正常"),
        (4, date(2026, 7, 2), "ORG003", "存放同业", "CNY", 38000000.00, 36000000.00, 2000000.00, "正常"),
    ],
}


def table_exists(cursor, table_name: str) -> bool:
    cursor.execute("SELECT COUNT(*) FROM USER_TABLES WHERE TABLE_NAME = ?", [table_name])
    return bool(cursor.fetchone()[0])


def main() -> None:
    connection = dmPython.connect(user=USERNAME, password=PASSWORD, server=HOST, port=PORT)
    cursor = connection.cursor()
    try:
        for table_name, ddl in TABLE_DEFINITIONS.items():
            if not table_exists(cursor, table_name):
                cursor.execute(ddl)
                print(f"created {table_name}")
            else:
                print(f"kept {table_name}")

        for table_name, rows in ROWS.items():
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = int(cursor.fetchone()[0])
            if count == 0 and rows:
                placeholders = ", ".join("?" for _ in rows[0])
                cursor.executemany(f"INSERT INTO {table_name} VALUES ({placeholders})", rows)
                print(f"inserted {len(rows)} rows into {table_name}")
            else:
                print(f"kept {table_name} with {count} rows")
        connection.commit()
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
