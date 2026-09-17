from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Computed,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from framework.common.enums.status_enum import StatusEnum
from framework.starter_tenant.entity.tenant_base_do import TenantBaseDO


class FileConfigDO(TenantBaseDO):
    __tablename__ = "infra_file_config"
    __table_args__ = (
        UniqueConstraint("tenant_id", "master_active", name="uq_infra_file_config_master_active"),
        Index("ix_infra_file_config_tenant", "tenant_id"),
        UniqueConstraint("tenant_id", "id", name="uq_infra_file_config_tenant_id"),
        {**TenantBaseDO.__table_args__, **{"comment": "文件配置表"}},
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="配置名")
    storage: Mapped[int] = mapped_column(Integer, nullable=False, comment="存储器（枚举类型）")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    status: Mapped[int] = mapped_column(
        SmallInteger, default=StatusEnum.ENABLE.code, comment="状态（1-启用，0-禁用）"
    )
    master: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否为主配置"
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, comment="文件客户端配置")
    master_active: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed("CASE WHEN deleted = 0 AND master = 1 THEN 1 ELSE NULL END"),
        comment="有效默认配置唯一标记",
    )
