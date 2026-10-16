"""初始化码值数据：6 个分类、12 个码值集、70 个码值项。

幂等：重复运行只会更新已存在记录，不会重复创建，也不会清空已有数据。
用法：.venv\\Scripts\\python.exe scripts\\seed_dict_codes.py
"""
from __future__ import annotations

from app.db import SessionLocal
from app.models import DictCategory, DictItem, DictSet

# 分类（编码、名称、排序、备注）
CATEGORIES = [
    ("AST_CLASS", "资产分类", 1, "金融资产会计分类"),
    ("BOND", "债券类", 2, "债券相关码值"),
    ("FUND_PRODUCT", "基金产品", 3, "基金类产品"),
    ("BOOK_OWNER", "账簿与归属", 4, "账簿类型与自营司库归属"),
    ("INTERBANK", "同业业务", 5, "同业存出/借款/理财等"),
    ("INTEREST", "计息与付息", 6, "计息基础与付息周期"),
]

# 码值集（编码、名称、所属分类编码、备注）
SETS = [
    ("astype", "金融资产分类", "AST_CLASS", "FVOCI/AC/FVTPL 等会计分类"),
    ("bondtp", "债券类型", "BOND", "国债、金融债、企业债等"),
    ("repttp", "报表债券类型", "BOND", "报表口径的债券细分类"),
    ("report_bscode", "报表资产负债类别", "BOND", "债券/存单/逆回购/同业/SPV非标"),
    ("prodkd_fund", "基金产品类型", "FUND_PRODUCT", "债基、货基等"),
    ("AccountBookType", "账簿类型", "BOOK_OWNER", "交易账簿/银行账簿"),
    ("sttype", "自营司库标记", "BOOK_OWNER", "自营/司库/未标记"),
    ("bktrtp_deposit", "同业存出类型", "INTERBANK", "线上/线下存放同业存出"),
    ("ty_booksave_astype", "同业业务类型", "INTERBANK", "拆出/理财/基金/存入/借款"),
    ("ofrdep", "是否同业存放", "INTERBANK", "0=否，1=是"),
    ("irbase", "计息基础", "INTEREST", "实际/360、实际/365 等"),
    ("pyperd", "付息周期", "INTEREST", "到期一次性、月、季、半年、年"),
]

# 码值项（所属码值集编码、编码、业务名称、排序）
ITEMS = [
    # astype - 金融资产分类（5 项）
    ("astype", "A", "以公允价值计量且其变动计入其他综合收益的金融资产(FVOCI)", 1),
    ("astype", "D", "应收账款类金融资产", 2),
    ("astype", "RR", "债券借贷标的券", 3),
    ("astype", "T", "以公允价值计量且其变动计入当期损益的金融资产(FVTPL)", 4),
    ("astype", "H", "以摊余成本计量的金融资产(AC)", 5),
    # bondtp - 债券类型（5 项）
    ("bondtp", "104", "企业债", 1),
    ("bondtp", "105", "其他", 2),
    ("bondtp", "101", "国债", 3),
    ("bondtp", "102", "金融债", 4),
    ("bondtp", "103", "央票", 5),
    # repttp - 报表债券类型（29 项，按用户提供的顺序）
    ("repttp", "B17", "储蓄国债", 1),
    ("repttp", "B01", "记账式国债", 2),
    ("repttp", "B07", "地方政府债券", 3),
    ("repttp", "B02", "央行票据", 4),
    ("repttp", "B03", "政策性银行债券", 5),
    ("repttp", "B22", "政府支持机构债", 6),
    ("repttp", "B04", "商业银行债券", 7),
    ("repttp", "B14", "证券公司债券", 8),
    ("repttp", "B15", "证券公司短期融资券", 9),
    ("repttp", "B48", "保险公司债券", 10),
    ("repttp", "B49", "信托公司债券", 11),
    ("repttp", "B50", "财务公司债券", 12),
    ("repttp", "B37", "金融租赁公司债券", 13),
    ("repttp", "B40", "汽车金融公司债券", 14),
    ("repttp", "B51", "消费金融公司债券", 15),
    ("repttp", "B08", "特种金融债", 16),
    ("repttp", "B52", "TLAC债券", 17),
    ("repttp", "B06", "其他商业性金融债", 18),
    ("repttp", "B09", "企业债", 19),
    ("repttp", "B24", "公司债", 20),
    ("repttp", "B31", "定向工具", 21),
    ("repttp", "B16", "短期融资券", 22),
    ("repttp", "B23", "超短期融资券", 23),
    ("repttp", "B11", "中期票据", 24),
    ("repttp", "B21", "集合票据", 25),
    ("repttp", "B44", "项目收益票据", 26),
    ("repttp", "B10", "资产支持证券", 27),
    ("repttp", "B18", "国际机构债券", 28),
    ("repttp", "B12", "其他债券", 29),
    # report_bscode - 报表资产负债类别（5 项）
    ("report_bscode", "1", "债券", 1),
    ("report_bscode", "2", "存单", 2),
    ("report_bscode", "3", "逆回购", 3),
    ("report_bscode", "4", "同业", 4),
    ("report_bscode", "5", "SPV/非标", 5),
    # prodkd_fund - 基金产品类型（4 项）
    ("prodkd_fund", "DKBOND_FUND", "摊余成本法定开债基", 1),
    ("prodkd_fund", "MARBOND_FUND", "市值法债基", 2),
    ("prodkd_fund", "FQSBOND_FUND", "发起式债基", 3),
    ("prodkd_fund", "CURRENCY_FUND", "货币市场基金", 4),
    # AccountBookType - 账簿类型（2 项）
    ("AccountBookType", "TRADEBOOK", "交易账簿", 1),
    ("AccountBookType", "BANKBOOK", "银行账簿", 2),
    # sttype - 自营司库标记（3 项，原 null 项已改为字符串 "未标记"）
    ("sttype", "0", "自营", 1),
    ("sttype", "1", "司库", 2),
    ("sttype", "未标记", "未标记", 3),
    # bktrtp_deposit - 同业存出类型（2 项）
    ("bktrtp_deposit", "50008", "线下存放同业存出", 1),
    ("bktrtp_deposit", "50057", "线上存放同业存出", 2),
    # ty_booksave_astype - 同业业务类型（5 项）
    ("ty_booksave_astype", "TYCC", "同业拆出", 1),
    ("ty_booksave_astype", "TYTZ", "同业理财产品投资", 2),
    ("ty_booksave_astype", "TYJJ", "基金投资", 3),
    ("ty_booksave_astype", "CFTY", "存放同业存入", 4),
    ("ty_booksave_astype", "TYJK", "同业借款", 5),
    # ofrdep - 是否同业存放（2 项）
    ("ofrdep", "0", "否", 1),
    ("ofrdep", "1", "是", 2),
    # irbase - 计息基础（3 项）
    ("irbase", "10", "实际/标准(31/360)", 1),
    ("irbase", "12", "实际/365(31/365)", 2),
    ("irbase", "11", "实际/实际(31/365,366)", 3),
    # pyperd - 付息周期（5 项）
    ("pyperd", "0", "到期一次性", 1),
    ("pyperd", "1", "月", 2),
    ("pyperd", "3", "季", 3),
    ("pyperd", "6", "半年", 4),
    ("pyperd", "12", "按年", 5),
]


def main() -> None:
    db = SessionLocal()
    try:
        # 1. 分类 upsert（按 category_code 匹配）
        cat_map: dict[str, DictCategory] = {}
        new_cat = upd_cat = 0
        for code, name, sort, remark in CATEGORIES:
            obj = db.query(DictCategory).filter(DictCategory.category_code == code).first()
            if obj is None:
                obj = DictCategory(category_code=code, category_name=name, sort=sort, remark=remark)
                db.add(obj)
                db.flush()
                new_cat += 1
                print(f"[+] 新建分类 {code} ({name})")
            else:
                obj.category_name = name
                obj.sort = sort
                obj.remark = remark
                upd_cat += 1
                print(f"[=] 更新分类 {code} ({name})")
            cat_map[code] = obj

        # 2. 码值集 upsert（按 set_code 匹配）
        set_map: dict[str, DictSet] = {}
        new_set = upd_set = 0
        for code, name, cat_code, remark in SETS:
            obj = db.query(DictSet).filter(DictSet.set_code == code).first()
            if obj is None:
                obj = DictSet(set_code=code, set_name=name, category_id=cat_map[cat_code].id,
                              status="enabled", remark=remark)
                db.add(obj)
                db.flush()
                new_set += 1
                print(f"[+] 新建码值集 {code} ({name})")
            else:
                obj.set_name = name
                obj.category_id = cat_map[cat_code].id
                obj.remark = remark
                # status 不强制改，避免误改停用状态
                upd_set += 1
                print(f"[=] 更新码值集 {code} ({name})")
            set_map[code] = obj

        # 3. 码值项 upsert（按 (set_id, item_code) 联合唯一）
        new_item = upd_item = 0
        for set_code, item_code, item_name, sort in ITEMS:
            s = set_map[set_code]
            obj = db.query(DictItem).filter(DictItem.set_id == s.id,
                                            DictItem.item_code == item_code).first()
            if obj is None:
                obj = DictItem(set_id=s.id, item_code=item_code, item_name=item_name,
                               sort=sort, status="enabled")
                db.add(obj)
                new_item += 1
            else:
                obj.item_name = item_name
                obj.sort = sort
                upd_item += 1
            print(f"    [{set_code}/{item_code}] {item_name}")

        db.commit()
        print(f"\n完成：分类 {new_cat} 新建 / {upd_cat} 更新"
              f" | 码值集 {new_set} 新建 / {upd_set} 更新"
              f" | 码值项 {new_item} 新建 / {upd_item} 更新")
        print(f"合计：{len(CATEGORIES)} 分类 / {len(SETS)} 码值集 / {len(ITEMS)} 码值项")
    except Exception as exc:
        db.rollback()
        print(f"失败，已回滚：{exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
