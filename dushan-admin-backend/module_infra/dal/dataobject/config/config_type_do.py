from datetime import datetime

from sqlalchemy import Computed, DateTime, Index, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from framework.common.enums import StatusEnum
from framework.starter_tenant.public import (
    TenantBaseDO,
)


class InfraConfigTypeDO(TenantBaseDO):
    __tablename__ = "infra_config_type"
    __table_args__ = (
        Index("ix_infra_config_type_tenant", "tenant_id"),
        UniqueConstraint("tenant_id", "id", name="uq_infra_config_type_tenant_id"),
        UniqueConstraint("tenant_id", "code", "active_key", name="uq_infra_config_type_active_0"),
        {**TenantBaseDO.__table_args__, **{"comment": "配置类型表"}},
    )

    module: Mapped[str] = mapped_column(
        String(50), nullable=False, default="", comment="所属模块标识"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, default="", comment="配置类型名称"
    )
    code: Mapped[str] = mapped_column(
        String(100), nullable=False, default="", comment="配置类型编码"
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, default=StatusEnum.ENABLE.code, comment="状态（1-启用，0-禁用）"
    )
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="备注")
    deleted_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="删除时间"
    )

    active_key: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed("CASE WHEN deleted = 0 THEN 1 ELSE NULL END"),
        comment="仅有效记录参与业务唯一约束",
    )
