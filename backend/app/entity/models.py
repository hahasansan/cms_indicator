from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Identity, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

"""SQLAlchemy ORM 实体定义。"""

from app.utils.database import Base


class DataModel(Base):
    __tablename__ = "data_models"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    module: Mapped[str] = mapped_column(String(64), default="未分类")
    table_name: Mapped[str] = mapped_column(String(128), nullable=False)
    owner: Mapped[str] = mapped_column(String(64), default ="当前用户")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="enabled")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    # 数据来源形态：table=实体表(默认) / report=报表子查询(逻辑映射)
    source_type: Mapped[str] = mapped_column(String(32), default="table")
    # source_type=report 时：报表解析后的基础 SQL(去掉可选参数块、已代入必填参数)
    source_sql: Mapped[str | None] = mapped_column(Text, nullable=True)
    # source_type=report 时：来源报表 ID(REPTID)
    source_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 报表原始 SQL 模板(含 [:参数])，跑批时按业务日期代入
    source_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 业务日期：balance=余额类(单日期) / period=时段类(起止)
    biz_date_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    biz_date_field: Mapped[str | None] = mapped_column(String(64), nullable=True)
    biz_date_start_param: Mapped[str | None] = mapped_column(String(64), nullable=True)
    biz_date_end_param: Mapped[str | None] = mapped_column(String(64), nullable=True)

    fields: Mapped[list["ModelField"]] = relationship(back_populates="model", cascade="all, delete-orphan")


class ModelField(Base):
    __tablename__ = "model_fields"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    model_id: Mapped[str] = mapped_column(ForeignKey("data_models.id"))
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    alias: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    data_type: Mapped[str] = mapped_column(String(32), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), default="")
    is_date: Mapped[bool] = mapped_column(Boolean, default=False)
    is_org: Mapped[bool] = mapped_column(Boolean, default=False)
    filterable: Mapped[bool] = mapped_column(Boolean, default=True)
    dict_set_id: Mapped[int | None] = mapped_column(ForeignKey("dict_sets.id"), nullable=True)

    model: Mapped[DataModel] = relationship(back_populates="fields")
    dict_set: Mapped["DictSet | None"] = relationship()


class Indicator(Base):
    __tablename__ = "indicators"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_id: Mapped[str | None] = mapped_column(ForeignKey("data_models.id"), nullable=True)
    parent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    category_id: Mapped[str] = mapped_column(String(64), default="root")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    period_type: Mapped[str] = mapped_column(String(16), default="point")  # point / period
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    field_map_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # FIELD1-25 的别名→列 映射
    sql_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    versions: Mapped[list["IndicatorVersion"]] = relationship(
        back_populates="indicator", cascade="all, delete-orphan"
    )
    schedules: Mapped[list["Schedule"]] = relationship(
        back_populates="indicator", cascade="all, delete-orphan"
    )


class IndicatorCategory(Base):
    __tablename__ = "indicator_categories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_id: Mapped[str] = mapped_column(String(64), default="root")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class IndicatorVersion(Base):
    __tablename__ = "indicator_versions"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    indicator_id: Mapped[str] = mapped_column(ForeignKey("indicators.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    sql_text: Mapped[str] = mapped_column(Text, nullable=False)
    saved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    indicator: Mapped[Indicator] = relationship(back_populates="versions")


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    indicator_id: Mapped[str] = mapped_column(ForeignKey("indicators.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    frequency: Mapped[str] = mapped_column(String(32), default="日")
    run_time: Mapped[str] = mapped_column(String(16), default="02:00")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    # 跑批配置：业务日期选项(JSON) + 指标范围
    date_option: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[str] = mapped_column(String(16), default="selected")  # selected / all / category
    category_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    indicator: Mapped[Indicator] = relationship(back_populates="schedules")


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    indicator_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    single_date: Mapped[str] = mapped_column(String(16), nullable=False)
    business_start_date: Mapped[str | None] = mapped_column(String(16), nullable=True)
    business_end_date: Mapped[str | None] = mapped_column(String(16), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    sql_text: Mapped[str] = mapped_column(Text, default="")
    message: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SqlFunction(Base):
    __tablename__ = "sql_functions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    function_type: Mapped[str] = mapped_column(String(16), nullable=False, default="custom")
    category: Mapped[str] = mapped_column(String(64), default="业务口径")
    usage_scope: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    render_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="scalar")
    template_sql: Mapped[str] = mapped_column(Text, nullable=False)
    args_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    return_type: Mapped[str] = mapped_column(String(32), default="NUMBER")
    description: Mapped[str] = mapped_column(Text, default="")
    example: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    editable: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class DictCategory(Base):
    """码值分类：风险类 / 机构类 / 产品类。"""
    __tablename__ = "dict_categories"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    category_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    category_name: Mapped[str] = mapped_column(String(128), nullable=False)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    sets: Mapped[list["DictSet"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )


class DictSet(Base):
    """码值集：贷款五级分类等。"""
    __tablename__ = "dict_sets"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("dict_categories.id"), nullable=False)
    set_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    set_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="enabled")
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    category: Mapped[DictCategory] = relationship(back_populates="sets")
    items: Mapped[list["DictItem"]] = relationship(
        back_populates="set", cascade="all, delete-orphan"
    )


class DictItem(Base):
    """码值项：正常 / 关注 / 次级 / 可疑 / 损失。"""
    __tablename__ = "dict_items"
    __table_args__ = (UniqueConstraint("set_id", "item_code", name="uq_dict_item_set_code"),)

    id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    set_id: Mapped[int] = mapped_column(ForeignKey("dict_sets.id"), nullable=False)
    item_code: Mapped[str] = mapped_column(String(64), nullable=False)
    item_name: Mapped[str] = mapped_column(String(128), nullable=False)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="enabled")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    set: Mapped[DictSet] = relationship(back_populates="items")
