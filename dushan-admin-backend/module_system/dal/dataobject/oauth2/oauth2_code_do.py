from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.public import (
    TenantBaseDO,
)


class OAuth2CodeDO(TenantBaseDO):
    __tablename__ = "system_oauth2_code"
    __table_args__ = (
        Index("ix_system_oauth2_code_tenant", "tenant_id"),
        UniqueConstraint("tenant_id", "code_digest", name="uq_system_oauth2_code_digest"),
        {**TenantBaseDO.__table_args__, **{"comment": "OAuth2 授权码表"}},
    )

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="用户编号")
    user_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="用户类型（枚举）【UserTypeEnum】"
    )
    code_digest: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="授权码 SHA-256 摘要"
    )
    client_id: Mapped[str] = mapped_column(String(255), nullable=False, comment="客户端编号")
    scopes: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, default=list, comment="授权范围 (JSON 数组)"
    )
    expires_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="过期时间")
    redirect_uri: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="可重定向的 URI 地址"
    )
    state: Mapped[str] = mapped_column(String(255), nullable=False, default="", comment="状态")

    consumed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="授权码是否已消费"
    )
