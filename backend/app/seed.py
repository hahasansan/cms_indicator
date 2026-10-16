from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import IndicatorCategory

# 字段→中文别名（数据源探查/模型导入时兜底命名用）
FIELD_ALIASES = {
    "DATA_DATE": "数据日期",
    "ORG_ID": "机构",
    "BOND_TYPE": "债券类型",
    "BOND_RATING": "债券评级",
    "REMAIN_TERM": "剩余期限",
    "FACE_VALUE": "持仓面值",
    "MARKET_VALUE": "持仓市值",
    "COST_VALUE": "持仓成本",
    "YTM": "到期收益率",
    "HOLD_STATUS": "持仓状态",
    "PRODUCT_TYPE": "产品类型",
    "CURRENCY": "币种",
    "DIRECTION": "交易方向",
    "TRADE_AMOUNT": "成交金额",
    "TRADE_RATE": "成交利率",
    "TRADE_COUNT": "成交笔数",
    "PRODUCT_CODE": "产品编码",
    "PRODUCT_NAME": "产品名称",
    "TENOR": "期限",
    "HIGH_PRICE": "最高价",
    "LOW_PRICE": "最低价",
    "CLOSE_PRICE": "收盘价",
    "PREV_DAY_CHANGE": "较前一日涨跌",
    "SOURCE_STATUS": "数据状态",
    "BOND_CODE": "债券编码",
    "BOND_NAME": "债券名称",
    "ACCOUNT_TYPE": "账户类型",
    "BALANCE": "余额",
    "AVAILABLE_AMOUNT": "可用金额",
    "FROZEN_AMOUNT": "冻结金额",
    "STATUS": "状态",
}



def init_database(db: Session) -> None:
    if not db.query(IndicatorCategory).first():
        db.add_all(
            [
                IndicatorCategory(id="root", name="全部指标", parent_id="", sort_order=0, enabled=True),
                IndicatorCategory(id="bond", name="债券业务", parent_id="root", sort_order=10, enabled=True),
                IndicatorCategory(id="fund", name="资金业务", parent_id="root", sort_order=20, enabled=True),
            ]
        )
    db.commit()
