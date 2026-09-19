from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Float,
    Index,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_data_permission.public import (
    data_permission,
)
from framework.starter_tenant.public import (
    TenantBaseDO,
)


@data_permission(
    permission_type="user_scope", user_id_column="user_id", description="操作日志记录-用户权限"
)
class OperateLogDO(TenantBaseDO):
    __tablename__ = "system_operate_log"
    __table_args__ = (
        Index("ix_system_operate_log_tenant", "tenant_id"),
        {**TenantBaseDO.__table_args__, **{"comment": "操作日志记录"}},
    )

    trace_id: Mapped[str] = mapped_column(String(64), default="", comment="链路追踪编号")
    user_id: Mapped[int] = mapped_column(BigInteger, comment="用户编号")
    user_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="用户类型（枚举）【UserTypeEnum】"
    )
    type: Mapped[str] = mapped_column(String(50), comment="操作模块类型")
    sub_type: Mapped[str] = mapped_column(String(50), comment="操作名")
    biz_id: Mapped[int] = mapped_column(BigInteger, comment="操作数据模块编号")
    action: Mapped[str] = mapped_column(Text, default="", comment="操作内容")
    extra: Mapped[str] = mapped_column(Text, default="", comment="拓展字段")
    request_method: Mapped[str] = mapped_column(String(16), comment="请求方法名")
    request_url: Mapped[str] = mapped_column(String(255), comment="请求地址")
    user_ip: Mapped[str] = mapped_column(String(50), comment="用户 IP")
    user_agent: Mapped[str] = mapped_column(String(200), comment="浏览器 UA")
    user_info: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False, comment="用户信息 (JSON 格式)"
    )

    event_id: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="审计预留编号")
    result: Mapped[str | None] = mapped_column(
        String(16), nullable=True, comment="pending/success/failure/cancelled"
    )
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True, comment="操作耗时毫秒")
    lease_until: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="审计预留有效期"
    )
