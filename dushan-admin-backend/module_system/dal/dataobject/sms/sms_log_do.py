from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, Index, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.public import (
    TenantBaseDO,
)
from module_system.definitions.enums.sms.sms_receive_status_enum import SmsReceiveStatusEnum
from module_system.definitions.enums.sms.sms_send_status_enum import SmsSendStatusEnum


class SmsLogDO(TenantBaseDO):
    __tablename__ = "system_sms_log"
    __table_args__ = (
        Index("ix_system_sms_log_tenant", "tenant_id"),
        {**TenantBaseDO.__table_args__, **{"comment": "短信日志表"}},
    )

    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="短信渠道编号")
    channel_code: Mapped[str] = mapped_column(String(63), nullable=False, comment="短信渠道编码")
    template_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="模板编号")
    template_code: Mapped[str] = mapped_column(String(63), nullable=False, comment="模板编码")
    template_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="短信类型【SmsTemplateTypeEnum】"
    )
    template_content: Mapped[str] = mapped_column(String(255), nullable=False, comment="短信内容")
    template_params: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="短信参数"
    )
    api_template_id: Mapped[str | None] = mapped_column(
        String(63), nullable=True, comment="短信 API 的模板编号"
    )
    mobile: Mapped[str] = mapped_column(String(11), nullable=False, comment="手机号")
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="用户编号")
    user_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="用户类型（枚举）【UserTypeEnum】"
    )
    send_status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=SmsSendStatusEnum.INIT.code, comment="发送状态"
    )
    send_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="发送时间")
    api_send_code: Mapped[str | None] = mapped_column(
        String(63), nullable=True, comment="短信 API 发送结果的编码"
    )
    api_send_msg: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="短信 API 发送失败的提示"
    )
    api_request_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="短信 API 发送返回的唯一请求 ID"
    )
    api_serial_no: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="短信 API 发送返回的序号"
    )
    receive_status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=SmsReceiveStatusEnum.INIT.code, comment="接收状态"
    )
    receive_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="接收时间"
    )
    api_receive_code: Mapped[str | None] = mapped_column(
        String(63), nullable=True, comment="API 接收结果的编码"
    )
    api_receive_msg: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="API 接收结果的说明"
    )

    send_claim_token: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="外发 claim 令牌"
    )
    send_claim_until: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="外发前 claim 到期时间"
    )
