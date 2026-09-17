from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import JSON, BigInteger, DateTime, Index, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_data_permission.decorators.data_permission import data_permission
from framework.starter_tenant.entity.tenant_base_do import TenantBaseDO


@data_permission(
    permission_type="user_scope", user_id_column="user_id", description="API访问日志-用户权限"
)
class ApiAccessLogDO(TenantBaseDO):
    __tablename__ = "infra_api_access_log"
    __table_args__ = (
        Index("ix_infra_api_access_log_tenant", "tenant_id"),
        {**TenantBaseDO.__table_args__, **{"comment": "API 访问日志表"}},
    )
    REQUEST_PARAMS_MAX_LENGTH: ClassVar[int] = 8000
    RESULT_MSG_MAX_LENGTH: ClassVar[int] = 512

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
    response_body: Mapped[Any | None] = mapped_column(
        JSON, nullable=True, comment="响应结果 (JSON格式)"
    )
    user_ip: Mapped[str] = mapped_column(String(50), nullable=False, comment="用户 IP")
    user_agent: Mapped[str] = mapped_column(String(200), nullable=False, comment="浏览器 UA")
    operate_module: Mapped[str] = mapped_column(String(100), nullable=False, comment="操作模块")
    operate_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="操作名")
    operate_type: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="操作分类（枚举类型）【OperateTypeEnum】"
    )
    begin_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="开始请求时间")
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="结束请求时间")
    duration: Mapped[int] = mapped_column(Integer, nullable=False, comment="执行时长，单位：毫秒")
    result_code: Mapped[int] = mapped_column(Integer, nullable=False, comment="结果码")
    result_msg: Mapped[str] = mapped_column(String(512), nullable=False, comment="结果提示")
