from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.public import (
    TenantBaseDO,
)


class OAuth2AccessTokenDO(TenantBaseDO):
    __tablename__ = "system_oauth2_access_token"
    __table_args__ = (
        Index("ix_system_oauth2_access_token_tenant", "tenant_id"),
        ForeignKeyConstraint(
            ["tenant_id", "refresh_token_id"],
            ["system_oauth2_refresh_token.tenant_id", "system_oauth2_refresh_token.id"],
            name="fk_system_oauth2_access_token_refresh_token_id",
        ),
        UniqueConstraint("tenant_id", "token_digest", name="uq_system_oauth2_access_token_digest"),
        Index("ix_system_oauth2_access_token_family", "tenant_id", "family_id"),
        {**TenantBaseDO.__table_args__, **{"comment": "OAuth2 访问令牌"}},
    )

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="用户编号")
    user_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="用户类型（枚举）【UserTypeEnum】"
    )
    user_info: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False, comment="用户信息 (JSON 格式)"
    )
    scopes: Mapped[list[str] | None] = mapped_column(
        JSON, default=list, nullable=True, comment="授权范围 (JSON 数组格式)"
    )
    token_digest: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="访问令牌 SHA-256 摘要"
    )
    refresh_token_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="刷新令牌记录编号"
    )
    client_id: Mapped[str] = mapped_column(String(255), nullable=False, comment="客户端编号")
    expires_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, comment="过期时间"
    )

    family_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="会话族编号")
    credential_revision: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="签发时的凭据版本"
    )
    revoked: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否撤销"
    )

    application_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="????")
    domain: Mapped[str] = mapped_column(String(64), nullable=False, comment="???")
