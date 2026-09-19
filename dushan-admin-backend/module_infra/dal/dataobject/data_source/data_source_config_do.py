from sqlalchemy import Boolean, Computed, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from framework.common.enums import StatusEnum
from framework.starter_tenant.public import (
    GlobalControlDO,
    global_model,
)
from module_infra.definitions.enums.data_source.data_source_type_enum import DataSourceTypeEnum


@global_model
class DataSourceConfigDO(GlobalControlDO):
    __tablename__ = "infra_data_source_config"
    __table_args__ = (
        UniqueConstraint(
            "source_type", "default_active", name="uq_infra_data_source_config_default_active"
        ),
        UniqueConstraint("name", "active_key", name="uq_infra_data_source_config_active_0"),
        {**GlobalControlDO.__table_args__, **{"comment": "数据源配置表"}},
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="数据源名称")
    url: Mapped[str] = mapped_column(String(500), nullable=False, comment="数据源连接URL")
    status: Mapped[int] = mapped_column(
        SmallInteger, default=StatusEnum.ENABLE.code, comment="状态：1-启用，0-禁用"
    )
    db_type: Mapped[str] = mapped_column(String(50), default="", comment="数据库类型")
    source_type: Mapped[int] = mapped_column(
        SmallInteger, default=DataSourceTypeEnum.MASTER.code, comment="数据源类型：1-主库，2-从库"
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否默认数据源")
    pool_size: Mapped[int] = mapped_column(SmallInteger, default=10, comment="连接池大小")
    max_overflow: Mapped[int] = mapped_column(SmallInteger, default=20, comment="最大溢出连接数")
    pool_recycle: Mapped[int] = mapped_column(
        SmallInteger, default=3600, comment="连接最大复用时间（秒）"
    )
    pool_timeout: Mapped[int] = mapped_column(
        SmallInteger, default=30, comment="获取连接最大等待时间（秒）"
    )
    echo: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否开启SQL日志")
    remark: Mapped[str | None] = mapped_column(String(500), comment="备注")
    active_key: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed("CASE WHEN deleted = 0 THEN 1 ELSE NULL END"),
        comment="仅有效记录参与业务唯一约束",
    )
    default_active: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed("CASE WHEN deleted = 0 AND is_default = 1 THEN 1 ELSE NULL END"),
        comment="有效默认配置唯一标记",
    )
