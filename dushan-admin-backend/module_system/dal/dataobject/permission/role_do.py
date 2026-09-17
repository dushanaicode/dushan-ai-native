from sqlalchemy import JSON, Computed, Index, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from framework.common.enums.builtin_type_enum import BuiltinTypeEnum
from framework.common.enums.status_enum import StatusEnum
from framework.starter_tenant.entity.tenant_base_do import TenantBaseDO
from module_system.definitions.enums.permission.permission_data_scope_enum import (
    PermissionDataScopeEnum,
)


class RoleDO(TenantBaseDO):
    __tablename__ = "system_role"
    __table_args__ = (
        Index("ix_system_role_tenant", "tenant_id"),
        UniqueConstraint("tenant_id", "code", "active_key", name="uq_system_role_active_0"),
        UniqueConstraint("tenant_id", "id", name="uq_system_role_tenant_id"),
        {**TenantBaseDO.__table_args__, **{"comment": "角色信息表"}},
    )

    name: Mapped[str] = mapped_column(String(30), nullable=False, comment="角色名称")
    code: Mapped[str] = mapped_column(String(100), nullable=False, comment="角色权限字符串")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, comment="显示顺序")
    data_scope: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=PermissionDataScopeEnum.ALL.code,
        comment="数据范围（1：全部数据权限 2：自定数据权限 3：本部门数据权限 4：本部门及以下数据权限 5：本人数据）",
    )
    data_scope_dept_ids: Mapped[list[int]] = mapped_column(
        JSON, nullable=False, default=list, comment="数据范围(指定部门数组)"
    )
    builtin: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=BuiltinTypeEnum.CUSTOM.code,
        comment="内置类型（1-内置 2-自定义）【BuiltinTypeEnum】",
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, default=StatusEnum.ENABLE.code, comment="开启状态（1-启用，0-禁用）"
    )
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="备注")

    active_key: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed("CASE WHEN deleted = 0 THEN 1 ELSE NULL END"),
        comment="仅有效记录参与业务唯一约束",
    )
