from sqlalchemy import JSON, BigInteger, Index, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from framework.common.enums.builtin_type_enum import BuiltinTypeEnum
from framework.common.enums.status_enum import StatusEnum
from framework.starter_tenant.entity.tenant_base_do import TenantBaseDO


class NoticeDO(TenantBaseDO):
    __tablename__ = "system_notification_notice"
    __table_args__ = (
        Index("ix_system_notification_notice_tenant", "tenant_id"),
        {**TenantBaseDO.__table_args__, **{"comment": "通知表"}},
    )

    code: Mapped[str | None] = mapped_column(
        String(63), nullable=True, default=None, comment="通知编码"
    )
    builtin: Mapped[int] = mapped_column(
        SmallInteger,
        default=BuiltinTypeEnum.CUSTOM.code,
        comment="内置类型（1-内置 2-自定义）【BuiltinTypeEnum】",
    )
    title: Mapped[str] = mapped_column(String(50), nullable=False, comment="通知标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="通知内容")
    type: Mapped[int] = mapped_column(Integer, nullable=False, comment="通知类型【NoticeTypeEnum】")
    user_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="用户类型【UserTypeEnum】"
    )
    channels: Mapped[list] = mapped_column(
        JSON, nullable=False, comment="通知渠道,参见 NotificationChannelEnum"
    )
    sms_template_code: Mapped[str] = mapped_column(
        String(63), nullable=True, default=None, comment="短信模板编码,选择SMS渠道时必填"
    )
    mail_account_id: Mapped[int] = mapped_column(
        BigInteger, nullable=True, default=None, comment="邮箱账号编号,选择MAIL渠道时必填"
    )
    publisher: Mapped[str] = mapped_column(String(64), nullable=False, comment="发布人")
    status: Mapped[int] = mapped_column(
        SmallInteger, default=StatusEnum.ENABLE.code, comment="开启状态（1-启用，0-禁用）"
    )
