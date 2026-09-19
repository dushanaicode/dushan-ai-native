from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.public import (
    TenantBaseDO,
)


class OAuth2ApproveDO(TenantBaseDO):
    __tablename__ = "system_oauth2_approve"
    __table_args__ = (
        Index("ix_system_oauth2_approve_tenant", "tenant_id"),
        {**TenantBaseDO.__table_args__, **{"comment": "OAuth2 批准表"}},
    )

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="用户编号")
    user_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="用户类型（枚举）【UserTypeEnum】"
    )
    client_id: Mapped[str] = mapped_column(String(255), nullable=False, comment="客户端编号")
    scope: Mapped[str] = mapped_column(String(255), nullable=False, default="", comment="授权范围")
    approved: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否接受")
    expires_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="过期时间")
