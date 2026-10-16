"""报表：列表、预览、导入为数据模型。"""
from __future__ import annotations

from fastapi import Depends, HTTPException, APIRouter, Query
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.core.config import get_dameng_config
from app.db import SessionLocal, get_db
from app.models import DataModel, ModelField
from app.routers.deps import report_row
from app.routers._model_import import (
    build_model_from_sql,
    do_sql_preview,
    do_sql_resolve_preview,
)
from app.schemas import BatchImportIn, ModelCreateIn, ReportImportIn, ResolvePreviewIn
from app.serializers import model_to_dict
from app.services.dameng import describe_query as dm_describe_query
from app.services.report_engine import (
    detect_biz_date,
)
from app.utils import new_id

router = APIRouter(tags=["报表"])


def import_report_model(payload: ModelCreateIn, db: Session) -> dict:
    reptid, reptna, sql_text = report_row(db, payload.reptid)
    code = f"RP{reptid}"
    if db.query(DataModel).filter(DataModel.code == code).first():
        raise HTTPException(400, "该报表已导入为数据模型")
    titles = db.execute(
        text("SELECT FILDCD, FILDNA FROM RP_TITLE WHERE REPTID = :rid ORDER BY ORDEBY, FILDCD"),
        {"rid": reptid},
    ).fetchall()
    return build_model_from_sql(
        db,
        payload,
        sql_text,
        code=code,
        name=reptna,
        module="报表",
        table_name=f"RPT_{reptid}",
        source_type="report",
        source_ref=reptid,
        source_template=sql_text,
        titles=titles,
    )


@router.get("/reports")
def list_reports(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=200),
    keyword: str = "",
    db: Session = Depends(get_db),
) -> dict:
    """分页查询报表列表，按 REPTID 倒序。keyword 搜索 REPTID/REPTNA。"""
    sql = "SELECT REPTID, REPTNA, REPTTP, SQLTXT FROM RP_REPORT"
    count_sql = "SELECT COUNT(*) FROM RP_REPORT"
    params: dict = {}
    if keyword:
        sql += " WHERE REPTID LIKE :kw OR REPTNA LIKE :kw"
        count_sql += " WHERE REPTID LIKE :kw OR REPTNA LIKE :kw"
        params["kw"] = f"%{keyword}%"
    total = int(db.execute(text(count_sql), params).scalar() or 0)
    sql += " ORDER BY REPTID DESC OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY"
    params["offset"] = (page - 1) * pageSize
    params["limit"] = pageSize
    rows = db.execute(text(sql), params).fetchall()
    title_counts = {
        str(r[0]): int(r[1]) for r in db.execute(text("SELECT REPTID, COUNT(*) FROM RP_TITLE GROUP BY REPTID")).fetchall()
    }
    imported = {
        str(r[0])
        for r in db.execute(text("SELECT SOURCE_REF FROM DATA_MODELS WHERE SOURCE_TYPE = 'report'")).fetchall()
        if r[0]
    }
    items = []
    for row in rows:
        reptid, reptna, repttp, sql_text = str(row[0]), str(row[1]), str(row[2] or ""), str(row[3] or "")
        biz = detect_biz_date(sql_text)
        items.append(
            {
                "reptid": reptid,
                "reptna": reptna,
                "repttp": repttp,
                "fieldCount": title_counts.get(reptid, 0),
                "bizDateType": (biz or {}).get("type"),
                "imported": reptid in imported,
            }
        )
    return {"items": items, "total": total, "page": page, "pageSize": pageSize}


@router.post("/reports/{reptid}/previews")
def preview_report(reptid: str, payload: ReportImportIn, db: Session = Depends(get_db)) -> dict:
    """代入业务日期示例值执行 SQL，返回字段列表（含可选块参数字段）和识别结果。"""
    _, _, sql_text = report_row(db, reptid)
    # 报表模式预览：先用公共 DESCRIBE，再叠加 RP_TITLE 信息
    _, biz_date_info = _resolve_biz_config_public(sql_text)
    from app.routers._model_import import _sample_dates, _build_all_fields
    from app.services.report_engine import resolve_report_for_date as _resolve
    sample_dates = _sample_dates(biz_date_info.get("type"), payload.sampleDate, payload.sampleStartDate, payload.sampleEndDate)
    resolved = _resolve(sql_text, biz_date_info, sample_dates)
    source = get_dameng_config()
    try:
        columns = dm_describe_query(source, resolved)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"报表 SQL 执行失败：{exc}") from exc
    output_map = {col["name"].lower(): col["dataType"] for col in columns}
    titles = db.execute(
        text("SELECT FILDCD, FILDNA FROM RP_TITLE WHERE REPTID = :rid ORDER BY ORDEBY, FILDCD"),
        {"rid": reptid},
    ).fetchall()
    fields = _build_all_fields(titles, columns, output_map, sql_text, biz_date_info)
    return {
        "reptid": reptid,
        "sqlText": resolved,
        "templateSql": sql_text,
        "columns": columns,
        "bizDate": biz_date_info,
        "fields": fields,
    }


def _resolve_biz_config_public(sql_text: str):
    """复用公共模块的 _resolve_biz_config（reports 内联 helper 已删）。"""
    from app.routers._model_import import _resolve_biz_config
    return _resolve_biz_config(sql_text)


@router.post("/reports/{reptid}/resolve-preview")
def resolve_preview(reptid: str, payload: ResolvePreviewIn, db: Session = Depends(get_db)) -> dict:
    """代入示例业务日期，返回替换后的 SQL，供用户核对参数是否指对。"""
    _, _, sql_text = report_row(db, reptid)
    result = do_sql_resolve_preview(db, sql_text, payload)
    result["reptid"] = reptid
    return result


@router.post("/reports/batch-import")
def batch_import(payload: BatchImportIn, db: Session = Depends(get_db)) -> dict:
    """批量导入报表为数据模型。

    每张报表使用独立 session（独立事务），互不影响，部分成功。
    返回 {success: [...], failed: [...]}。
    """
    # 只校验一次连接可用性
    source = get_dameng_config()

    success: list[dict] = []
    failed: list[dict] = []

    # 预先查询报表名（失败时也能展示名称）
    name_map: dict[str, str] = {}
    if payload.reptids:
        rows = db.execute(
            text("SELECT REPTID, REPTNA FROM RP_REPORT WHERE REPTID IN :ids"),
            {"ids": payload.reptids},
        ).fetchall()
        for r in rows:
            name_map[str(r[0])] = str(r[1])

    for reptid in payload.reptids:
        sub_db = SessionLocal()
        try:
            model = import_report_model(
                ModelCreateIn(
                    reptid=reptid,
                    fields=[],  # 全自动识别字段配置
                    sampleDate=payload.sampleDate,
                    sampleStartDate=payload.sampleStartDate,
                    sampleEndDate=payload.sampleEndDate,
                ),
                sub_db,
            )
            success.append({
                "reptid": reptid,
                "reptna": model.get("name") or name_map.get(reptid, ""),
                "modelId": model.get("id", ""),
            })
        except HTTPException as exc:
            failed.append({"reptid": reptid, "reptna": name_map.get(reptid, ""), "error": str(exc.detail)})
        except Exception as exc:  # noqa: BLE001
            sub_db.rollback()
            failed.append({"reptid": reptid, "reptna": name_map.get(reptid, ""), "error": str(exc)})
        finally:
            sub_db.close()

    return {"success": success, "failed": failed}
