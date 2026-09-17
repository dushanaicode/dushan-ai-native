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


class UserRoleDO(TenantBaseDO):
    __tablename__ = "system_user_role"
    __table_args__ = (
        Index("ix_system_user_role_tenant", "tenant_id"),
        UniqueConstraint(
            "tenant_id", "user_id", "role_id", "active_key", name="uq_system_user_role_active_0"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "user_id"],
            ["system_users.tenant_id", "system_users.id"],
            name="fk_system_user_role_user_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "role_id"],
            ["system_role.tenant_id", "system_role.id"],
            name="fk_system_user_role_role_id",
        ),
        {**TenantBaseDO.__table_args__, **{"comment": "用户角色关联表"}},
    )

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="用户ID")
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="角色ID")

    active_key: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed("CASE WHEN deleted = 0 THEN 1 ELSE NULL END"),
        comment="仅有效记录参与业务唯一约束",
    )
