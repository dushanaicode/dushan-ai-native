from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.entity.tenant_base_do import TenantBaseDO


class OAuth2RefreshTokenDO(TenantBaseDO):
    __tablename__ = "system_oauth2_refresh_token"
    __table_args__ = (
        Index("ix_system_oauth2_refresh_token_tenant", "tenant_id"),
        UniqueConstraint("tenant_id", "id", name="uq_system_oauth2_refresh_token_tenant_id"),
        UniqueConstraint("tenant_id", "token_digest", name="uq_system_oauth2_refresh_token_digest"),
        Index("ix_system_oauth2_refresh_token_family", "tenant_id", "family_id"),
        {**TenantBaseDO.__table_args__, **{"comment": "OAuth2 刷新令牌"}},
    )

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="用户编号")
    token_digest: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="刷新令牌 SHA-256 摘要"
    )
    user_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="用户类型（枚举）【UserTypeEnum】"
    )
    client_id: Mapped[str] = mapped_column(String(255), nullable=False, comment="客户端编号")
    scopes: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, comment="授权范围 (存储为JSON)"
    )
    expires_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="过期时间")

    family_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="会话族编号")
    credential_revision: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="签发时的凭据版本"
    )
    revoked: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否撤销"
    )
    consumed_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="轮换消费时间，保留记录用于重放检测"
    )

    application_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="????")
    domain: Mapped[str] = mapped_column(String(64), nullable=False, comment="???")
