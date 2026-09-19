from sqlalchemy import (
    BigInteger,
    Computed,
    ForeignKeyConstraint,
    Index,
    SmallInteger,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.public import (
    TenantBaseDO,
)


class RoleMenuDO(TenantBaseDO):
    __tablename__ = "system_role_menu"
    __table_args__ = (
        Index("ix_system_role_menu_tenant", "tenant_id"),
        UniqueConstraint(
            "tenant_id", "role_id", "menu_id", "active_key", name="uq_system_role_menu_active_0"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "role_id"],
            ["system_role.tenant_id", "system_role.id"],
            name="fk_system_role_menu_role_id",
        ),
        {**TenantBaseDO.__table_args__, **{"comment": "角色和菜单关联表"}},
    )

    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="角色ID")
    menu_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="菜单ID")

    active_key: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed("CASE WHEN deleted = 0 THEN 1 ELSE NULL END"),
        comment="仅有效记录参与业务唯一约束",
    )
