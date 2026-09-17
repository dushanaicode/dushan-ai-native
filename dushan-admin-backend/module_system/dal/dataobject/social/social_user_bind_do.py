from sqlalchemy import (
    BigInteger,
    Computed,
    ForeignKeyConstraint,
    Index,
    SmallInteger,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.entity.tenant_base_do import TenantBaseDO


class SocialUserBindDO(TenantBaseDO):
    __tablename__ = "system_social_user_bind"
    __table_args__ = (
        Index("ix_system_social_user_bind_tenant", "tenant_id"),
        UniqueConstraint(
            "tenant_id",
            "user_type",
            "social_type",
            "social_user_id",
            "active_key",
            name="uq_system_social_user_bind_active_0",
        ),
        UniqueConstraint(
            "tenant_id",
            "user_type",
            "social_type",
            "user_id",
            "active_key",
            name="uq_system_social_user_bind_active_1",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "social_user_id"],
            ["system_social_user.tenant_id", "system_social_user.id"],
            name="fk_system_social_user_bind_social_user_id",
        ),
        {**TenantBaseDO.__table_args__, **{"comment": "社交绑定表"}},
    )

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="用户编号")
    user_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="用户类型（枚举）【UserTypeEnum】"
    )
    social_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="社交平台的类型【SocialTypeEnum】"
    )
    social_user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="社交用户的编号"
    )

    active_key: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed("CASE WHEN deleted = 0 THEN 1 ELSE NULL END"),
        comment="仅有效记录参与业务唯一约束",
    )
