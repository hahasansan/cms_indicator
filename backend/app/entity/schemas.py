"""API 请求和响应的数据结构。"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    """分页返回结构。"""
    items: list[T]
    total: int
    page: int
    pageSize: int


class FieldIn(BaseModel):
    alias: str
    role: str
    dataType: str | None = None
    unit: str | None = ""
    isDate: bool = False
    isOrg: bool = False
    filterable: bool = True
    dictSetId: int | None = None


class IndicatorIn(BaseModel):
    name: str
    modelId: str
    parentId: str | None = None
    status: str = "draft"
    categoryId: str = "root"
    periodType: str = "point"  # point / period
    config: dict[str, Any]


class IndicatorCategoryIn(BaseModel):
    name: str
    parentId: str = "root"
    sortOrder: int = 0
    enabled: bool = True


class FavoriteIn(BaseModel):
    favorite: bool = True


class SqlPreviewIn(BaseModel):
    config: dict[str, Any]


class RunIn(BaseModel):
    runDate: str = "2026-07-10"
    dateOption: dict | None = None  # {type:balance/period, single:{}, start:{}, end:{}}


class ScheduleIn(BaseModel):
    indicatorId: str
    name: str
    frequency: str = "日"
    runTime: str = "02:00"
    enabled: bool = True
    dateOption: dict | None = None
    scope: str = "selected"  # selected / all / category
    categoryId: str = ""


class BatchRunIn(BaseModel):
    indicatorIds: list[str] = Field(default_factory=list)
    scope: str = "selected"  # selected / all / category
    categoryId: str = ""
    dateOption: dict | None = None


class FieldOverride(BaseModel):
    """导入时字段配置覆盖。"""
    field_name: str
    alias: str = ""
    role: str = "normal"          # dimension / measure / normal
    data_type: str = ""
    is_date: bool = False
    is_org: bool = False
    filterable: bool = True


class ReportImportIn(BaseModel):
    """报表预览请求：示例值（用于执行 SQL 拿字段）。"""
    reptid: str = ""
    sampleDate: str = "2026-08-20"
    sampleStartDate: str = "2026-08-01"
    sampleEndDate: str = "2026-08-31"


class SqlTemplatePreviewIn(BaseModel):
    """自定义 SQL 预览请求：模板 SQL + 示例值。"""
    sqlText: str
    sampleDate: str = "2026-08-20"
    sampleStartDate: str = "2026-08-01"
    sampleEndDate: str = "2026-08-31"


class ModelCreateIn(BaseModel):
    """创建数据模型：通过报表导入或自定义SQL导入。"""
    code: str = ""
    name: str = ""
    module: str = "业务模块"
    owner: str = "当前用户"
    description: str = ""
    reptid: str = ""
    fields: list[FieldOverride] = Field(default_factory=list)
    # 示例值：导入时执行 SQL 拿字段用，不持久化
    sampleDate: str = "2026-08-20"
    sampleStartDate: str = "2026-08-01"
    sampleEndDate: str = "2026-08-31"
    # 自定义 SQL 导入
    sqlText: str = ""
    tableName: str = ""   # 自定义 SQL 模式下的占位表名，如 T_CUSTOM_SQL_1；报表模式默认 RPT_{reptid}


class ResolvePreviewIn(BaseModel):
    """代入示例业务日期预览请求（报表模式）。"""
    reptid: str = ""
    bizDateType: str = "none"       # balance / period / none
    bizDateField: str = ""
    bizDateStartParam: str = ""
    bizDateEndParam: str = ""
    sampleDate: str = "2026-08-20"
    sampleStartDate: str = "2026-08-01"
    sampleEndDate: str = "2026-08-31"


class SqlResolvePreviewIn(BaseModel):
    """代入示例业务日期预览请求（自定义 SQL 模式）。"""
    sqlText: str
    bizDateType: str = "none"
    bizDateField: str = ""
    bizDateStartParam: str = ""
    bizDateEndParam: str = ""
    sampleDate: str = "2026-08-20"
    sampleStartDate: str = "2026-08-01"
    sampleEndDate: str = "2026-08-31"


class BatchImportIn(BaseModel):
    """批量导入报表为数据模型：每张表独立事务，部分成功。"""
    reptids: list[str] = Field(default_factory=list)
    sampleDate: str = "2026-08-20"
    sampleStartDate: str = "2026-08-01"
    sampleEndDate: str = "2026-08-31"


class DictCategoryIn(BaseModel):
    """码值分类新增 / 编辑入参。"""
    categoryCode: str
    categoryName: str
    sort: int = 0
    remark: str = ""


class DictSetIn(BaseModel):
    """码值集新增 / 编辑入参。"""
    categoryId: int
    setCode: str
    setName: str
    status: str = "enabled"   # enabled / disabled
    remark: str = ""


class DictItemIn(BaseModel):
    """码值项新增 / 编辑入参。"""
    itemCode: str
    itemName: str
    sort: int = 0
    status: str = "enabled"
