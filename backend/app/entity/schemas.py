"""API 请求和响应的数据结构。

重要约束：达梦数据库空字符串会被当作 NULL 处理，非空字段不可传入空字符串值。
因此所有 NOT NULL 字段在 Schema 层统一使用 min_length=1 拒绝空串，并在路由层再次校验。
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, model_validator

T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    """分页返回结构。"""
    items: list[T]
    total: int
    page: int
    pageSize: int


# ============================================================
# 模型与字段
# ============================================================
class FieldIn(BaseModel):
    """模型字段编辑入参。"""
    alias: str = Field(..., min_length=1, description="业务名称，必填")
    role: str = Field(..., min_length=1, description="字段角色，必填：dimension/measure/normal")
    dataType: str | None = Field(default=None, description="数据类型（仅展示用）")
    unit: str | None = Field(default=None)
    isDate: bool = False
    isOrg: bool = False
    filterable: bool = True
    dictSetId: int | None = None


class FieldOverride(BaseModel):
    """导入时字段配置覆盖（可全部留空，后端会自动填）。"""
    field_name: str = Field(..., min_length=1)
    alias: str = ""
    role: str = ""
    data_type: str = ""
    is_date: bool = False
    is_org: bool = False
    filterable: bool = True


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


class ModelSqlUpdateIn(BaseModel):
    """更新自定义 SQL 模型的 SQL 模板。"""
    sqlText: str = Field(..., min_length=1)
    sampleDate: str = "2026-08-20"
    sampleStartDate: str = "2026-08-01"
    sampleEndDate: str = "2026-08-31"


# ============================================================
# 指标
# ============================================================
class IndicatorIn(BaseModel):
    name: str = Field(..., min_length=1)
    modelId: str = Field(..., min_length=1)
    parentId: str | None = None
    status: str = "draft"
    categoryId: str = "root"
    periodType: str = "point"  # point / period
    config: dict[str, Any]


class IndicatorCategoryIn(BaseModel):
    name: str = Field(..., min_length=1)
    parentId: str = "root"
    sortOrder: int = 0
    enabled: bool = True


class FavoriteIn(BaseModel):
    favorite: bool = True


# ============================================================
# 运行 / SQL 预览
# ============================================================
class SqlPreviewIn(BaseModel):
    config: dict[str, Any]
    dateOption: dict | None = None


class RunIn(BaseModel):
    runDate: str = "2026-07-10"
    dateOption: dict | None = None  # {type:balance/period, single:{}, start:{}, end:{}}


# ============================================================
# 调度
# ============================================================
class ScheduleIn(BaseModel):
    indicatorId: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
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


# ============================================================
# 度量公式
# ============================================================
class MeasureFunctionIn(BaseModel):
    code: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    formula: str = Field(..., min_length=1)
    description: str = ""
    parameters: list[str] | None = None


# ============================================================
# 报表导入 / 预览
# ============================================================
class ReportImportIn(BaseModel):
    """报表预览请求：示例值（用于执行 SQL 拿字段）。"""
    reptid: str = ""
    sampleDate: str = "2026-08-20"
    sampleStartDate: str = "2026-08-01"
    sampleEndDate: str = "2026-08-31"


class SqlTemplatePreviewIn(BaseModel):
    """自定义 SQL 预览请求：模板 SQL + 示例值。"""
    sqlText: str = Field(..., min_length=1)
    sampleDate: str = "2026-08-20"
    sampleStartDate: str = "2026-08-01"
    sampleEndDate: str = "2026-08-31"


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
    sqlText: str = Field(..., min_length=1)
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


# ============================================================
# 码值
# ============================================================
class DictCategoryIn(BaseModel):
    """码值分类新增 / 编辑入参。"""
    categoryCode: str = Field(..., min_length=1)
    categoryName: str = Field(..., min_length=1)
    sort: int = 0
    remark: str = ""


class DictSetIn(BaseModel):
    """码值集新增 / 编辑入参。"""
    categoryId: int = Field(..., description="所属分类 ID，外键，必填")
    setCode: str = Field(..., min_length=1)
    setName: str = Field(..., min_length=1)
    status: str = "enabled"   # enabled / disabled
    remark: str = ""


class DictItemIn(BaseModel):
    """码值项新增 / 编辑入参。"""
    itemCode: str = Field(..., min_length=1)
    itemName: str = Field(..., min_length=1)
    sort: int = 0
    status: str = "enabled"
