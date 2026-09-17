from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Computed,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from framework.common.enums.status_enum import StatusEnum
from framework.starter_data_permission.decorators.data_permission import data_permission
from framework.starter_tenant.entity.tenant_base_do import TenantBaseDO
from module_system.definitions.enums.common.common_sex_enum import CommonSexEnum


@data_permission(
    permission_type="both",
    user_id_column="id",
    dept_id_column="dept_id",
    description="用户表-用户部门权限",
)
class AdminUserDO(TenantBaseDO):
    __tablename__ = "system_users"
    __table_args__ = (
        Index("ix_system_users_tenant", "tenant_id"),
        UniqueConstraint("tenant_id", "username", "active_key", name="uq_system_users_active_0"),
        UniqueConstraint("tenant_id", "id", name="uq_system_users_tenant_id"),
        ForeignKeyConstraint(
            ["tenant_id", "dept_id"],
            ["system_dept.tenant_id", "system_dept.id"],
            name="fk_system_users_dept_id",
        ),
        {**TenantBaseDO.__table_args__, **{"comment": "用户信息表"}},
    )

    username: Mapped[str] = mapped_column(String(30), nullable=False, comment="用户账号")
    password: Mapped[str] = mapped_column(String(100), default="", comment="密码")
    nickname: Mapped[str | None] = mapped_column(String(30), nullable=True, comment="用户昵称")
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="备注")
    dept_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="部门ID")
    post_ids: Mapped[list[int] | None] = mapped_column(
        JSON, nullable=True, comment="岗位编号列表（JSON 格式）"
    )
    email: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default="", comment="用户邮箱"
    )
    mobile: Mapped[str | None] = mapped_column(
        String(11), nullable=True, default="", comment="手机号码"
    )
    sex: Mapped[int] = mapped_column(
        SmallInteger, nullable=True, default=CommonSexEnum.UNKNOWN.code, comment="用户性别"
    )
    avatar: Mapped[str | None] = mapped_column(
        String(512), nullable=True, default="", comment="头像地址"
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, default=StatusEnum.ENABLE.code, comment="开启状态（1-启用，0-禁用）"
    )
    login_ip: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default="", comment="最后登录IP"
    )
    login_date: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="最后登录时间"
    )

    active_key: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed("CASE WHEN deleted = 0 THEN 1 ELSE NULL END"),
        comment="仅有效记录参与业务唯一约束",
    )

    credential_revision: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, comment="凭据版本，改密或账号状态变化时递增"
    )
    authorization_revision: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, comment="权限版本，与授权变化原子提交"
    )
