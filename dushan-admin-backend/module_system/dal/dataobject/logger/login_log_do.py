from sqlalchemy import BigInteger, Index, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_data_permission.public import (
    data_permission,
)
from framework.starter_tenant.public import (
    TenantBaseDO,
)


@data_permission(
    permission_type="user_scope", user_id_column="user_id", description="系统访问记录-用户权限"
)
class LoginLogDO(TenantBaseDO):
    __tablename__ = "system_login_log"
    __table_args__ = (
        Index("ix_system_login_log_tenant", "tenant_id"),
        {**TenantBaseDO.__table_args__, **{"comment": "系统访问记录"}},
    )

    log_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="日志类型（枚举）【LoginLogTypeEnum】"
    )
    trace_id: Mapped[str] = mapped_column(String(64), default="", comment="链路追踪编号")
    user_id: Mapped[int] = mapped_column(BigInteger, default=0, comment="用户编号")
    user_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="用户类型（枚举）【UserTypeEnum】"
    )
    username: Mapped[str] = mapped_column(String(50), default="", comment="用户账号")
    result: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="登录结果（枚举）【LoggerLoginResultEnum】"
    )
    user_ip: Mapped[str] = mapped_column(String(50), comment="用户IP")
    user_agent: Mapped[str] = mapped_column(String(512), comment="浏览器UA")
