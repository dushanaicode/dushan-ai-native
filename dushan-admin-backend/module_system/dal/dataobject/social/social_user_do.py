from sqlalchemy import Computed, Index, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.entity.tenant_base_do import TenantBaseDO


class SocialUserDO(TenantBaseDO):
    __tablename__ = "system_social_user"
    __table_args__ = (
        Index("ix_system_social_user_tenant", "tenant_id"),
        UniqueConstraint(
            "tenant_id",
            "type",
            "openid",
            "client_id",
            "subject_type",
            "application_id",
            "active_key",
            name="uq_system_social_user_active_0",
        ),
        UniqueConstraint("tenant_id", "id", name="uq_system_social_user_tenant_id"),
        {**TenantBaseDO.__table_args__, **{"comment": "社交用户表"}},
    )

    type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="社交平台的类型【SocialTypeEnum】"
    )
    openid: Mapped[str] = mapped_column(
        String(32).with_variant(String(32, collation="utf8mb4_bin"), "mysql"),
        nullable=False,
        comment="社交 openid",
    )
    token: Mapped[str | None] = mapped_column(String(256), nullable=True, comment="社交 token")
    raw_token_info: Mapped[str] = mapped_column(
        Text, nullable=False, comment="原始 Token 数据，一般是 JSON 格式"
    )
    nickname: Mapped[str] = mapped_column(String(32), nullable=False, comment="用户昵称")
    avatar: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="用户头像")
    raw_user_info: Mapped[str] = mapped_column(
        Text, nullable=False, comment="原始用户数据，一般是 JSON 格式"
    )
    code: Mapped[str] = mapped_column(
        String(256).with_variant(String(256, collation="utf8mb4_bin"), "mysql"),
        nullable=False,
        comment="最后一次的认证 code",
    )
    state: Mapped[str | None] = mapped_column(
        String(256).with_variant(String(256, collation="utf8mb4_bin"), "mysql"),
        nullable=True,
        comment="最后一次的认证 state",
    )

    active_key: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed("CASE WHEN deleted = 0 THEN 1 ELSE NULL END"),
        comment="仅有效记录参与业务唯一约束",
    )

    client_id: Mapped[str] = mapped_column(String(255), nullable=False, comment="第三方应用编号")
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="第三方主体类型")
    application_id: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="本站社交应用标识"
    )
