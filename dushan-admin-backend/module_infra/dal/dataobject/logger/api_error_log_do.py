from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import JSON, BigInteger, DateTime, Index, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_data_permission.decorators.data_permission import data_permission
from framework.starter_tenant.entity.tenant_base_do import TenantBaseDO
from module_infra.definitions.enums.logger.api_error_log_process_status_enum import (
    ApiErrorLogProcessStatusEnum,
)


@data_permission(
    permission_type="user_scope", user_id_column="user_id", description="API错误日志-用户权限"
)
class ApiErrorLogDO(TenantBaseDO):
    __tablename__ = "infra_api_error_log"
    __table_args__ = (
        Index("ix_infra_api_error_log_tenant", "tenant_id"),
        {**TenantBaseDO.__table_args__, **{"comment": "API 错误日志表"}},
    )
    REQUEST_PARAMS_MAX_LENGTH: ClassVar[int] = 8000

    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="链路追踪编号")
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="用户编号")
    user_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="用户类型（枚举）【UserTypeEnum】"
    )
    application_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="应用名")
    request_method: Mapped[str] = mapped_column(String(10), nullable=False, comment="请求方法名")
    request_url: Mapped[str] = mapped_column(String(255), nullable=False, comment="访问地址")
    request_params: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="请求参数 (JSON格式)"
    )
    user_ip: Mapped[str] = mapped_column(String(50), nullable=False, comment="用户 IP")
    user_agent: Mapped[str] = mapped_column(String(200), nullable=False, comment="浏览器 UA")
    exception_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="异常发生时间"
    )
    exception_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="异常名")
    exception_message: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="异常导致的消息"
    )
    exception_root_cause_message: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="异常导致的根消息"
    )
    exception_stack_trace: Mapped[str] = mapped_column(Text, nullable=False, comment="异常的栈轨迹")
    exception_class_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="异常发生的类全名"
    )
    exception_file_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="异常发生的类文件"
    )
    exception_method_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="异常发生的方法名"
    )
    exception_line_number: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="异常发生的方法所在行"
    )
    process_status: Mapped[int] = mapped_column(
        SmallInteger,
        default=ApiErrorLogProcessStatusEnum.INIT.code,
        nullable=False,
        comment="处理状态",
    )
    process_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="处理时间"
    )
    process_user_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="处理用户编号"
    )
