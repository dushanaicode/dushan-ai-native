from typing import Any

from sqlalchemy import JSON, Computed, Index, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import expression

from framework.common.enums import StatusEnum
from framework.starter_tenant.public import (
    TenantBaseDO,
)


class SocialClientDO(TenantBaseDO):
    __tablename__ = "system_social_client"
    __table_args__ = (
        Index("ix_system_social_client_tenant", "tenant_id"),
        UniqueConstraint(
            "tenant_id",
            "social_type",
            "user_type",
            "active_key",
            name="uq_system_social_client_active_0",
        ),
        {**TenantBaseDO.__table_args__, **{"comment": "社交客户端表"}},
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="应用名")
    social_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="社交平台的类型【SocialTypeEnum】"
    )
    user_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="用户类型（枚举）【UserTypeEnum】"
    )
    client_id: Mapped[str] = mapped_column(String(255), nullable=False, comment="客户端编号")
    client_secret: Mapped[str] = mapped_column(String(255), nullable=False, comment="客户端密钥")
    agent_id: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="代理编号")
    auth_config: Mapped[dict[str, Any]] = mapped_column(
        JSON, server_default=expression.text("('{}')"), comment="认证配置，JSON格式"
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, default=StatusEnum.ENABLE.code, comment="开启状态（1-启用，0-禁用）"
    )

    active_key: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed("CASE WHEN deleted = 0 THEN 1 ELSE NULL END"),
        comment="仅有效记录参与业务唯一约束",
    )
