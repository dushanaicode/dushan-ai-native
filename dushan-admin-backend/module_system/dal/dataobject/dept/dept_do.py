from sqlalchemy import BigInteger, Index, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from framework.common.enums import StatusEnum
from framework.starter_tenant.public import (
    TenantBaseDO,
)


class DeptDO(TenantBaseDO):
    __tablename__ = "system_dept"
    __table_args__ = (
        Index("ix_system_dept_tenant", "tenant_id"),
        UniqueConstraint("tenant_id", "id", name="uq_system_dept_tenant_id"),
        {**TenantBaseDO.__table_args__, **{"comment": "部门信息表"}},
    )

    name: Mapped[str] = mapped_column(String(30), nullable=False, default="", comment="部门名称")
    parent_id: Mapped[int] = mapped_column(BigInteger, default=0, comment="父部门id")
    sort: Mapped[int] = mapped_column(Integer, default=0, comment="显示顺序")
    leader_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="负责人")
    phone: Mapped[str | None] = mapped_column(String(11), nullable=True, comment="联系电话")
    email: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="邮箱")
    status: Mapped[int] = mapped_column(
        SmallInteger,
        default=StatusEnum.ENABLE.code,
        comment="开启状态（1-启用，0-禁用）【StatusEnum】",
    )

    # 定义根部门的父部门 ID 常量
    PARENT_ID_ROOT: int = 0
