from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.public import (
    TenantBaseDO,
)
from module_system.definitions.enums.mail.mail_send_status_enum import MailSendStatusEnum


class MailLogDO(TenantBaseDO):
    __tablename__ = "system_mail_log"
    __table_args__ = ({**TenantBaseDO.__table_args__, **{"comment": "邮件日志表"}},)

    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="用户编号")
    user_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="用户类型（枚举）【UserTypeEnum】"
    )
    to_mail: Mapped[str] = mapped_column(Text, nullable=False, comment="接收邮箱地址(多个逗号分隔)")
    cc_mail: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="抄送邮箱地址(多个逗号分隔)"
    )
    bcc_mail: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="密送邮箱地址(多个逗号分隔)"
    )
    account_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="邮箱账号编号")
    from_mail: Mapped[str] = mapped_column(String(255), nullable=False, comment="发送邮箱地址")
    template_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="模板编号")
    template_code: Mapped[str] = mapped_column(String(63), nullable=False, comment="模板编码")
    template_nickname: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="模版发送人名称"
    )
    template_title: Mapped[str] = mapped_column(String(255), nullable=False, comment="邮件标题")
    template_content: Mapped[str] = mapped_column(Text, nullable=False, comment="邮件内容")
    template_params: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="邮件参数"
    )
    send_status: Mapped[int] = mapped_column(
        SmallInteger, default=MailSendStatusEnum.INIT.code, comment="发送状态【MailSendStatusEnum】"
    )
    send_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="发送时间")
    send_message_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="发送返回的消息 ID"
    )
    send_exception: Mapped[str | None] = mapped_column(Text, nullable=True, comment="发送异常")

    send_claim_token: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="外发 claim 令牌"
    )
    send_claim_until: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="外发前 claim 到期时间"
    )
