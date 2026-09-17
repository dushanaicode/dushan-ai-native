from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_data_permission.decorators.data_permission import data_permission
from framework.starter_tenant.entity.tenant_base_do import TenantBaseDO


@data_permission(
    permission_type="user_scope", user_id_column="user_id", description="站内信消息表-用户权限"
)
class NoticeMessageDO(TenantBaseDO):
    __tablename__ = "system_notification_message"
    __table_args__ = (
        Index("ix_system_notification_message_tenant", "tenant_id"),
        {**TenantBaseDO.__table_args__, **{"comment": "站内信消息表"}},
    )

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="用户id")
    user_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="用户类型（枚举）【UserTypeEnum】"
    )
    notice_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="关联的通知编号")
    notice_log_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        default=None,
        comment="通知日志ID (system_notification_notice_log.id)",
    )
    notice_title: Mapped[str] = mapped_column(String(100), nullable=False, comment="通知标题")
    notice_content: Mapped[str] = mapped_column(Text, nullable=False, comment="通知内容")
    notice_type: Mapped[int] = mapped_column(Integer, nullable=False, comment="通知类型")
    publisher_info: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=True, comment="发布者信息"
    )
    sent_channels: Mapped[list] = mapped_column(
        JSON, nullable=False, comment="实际发送的渠道,参见 NotificationChannelEnum"
    )
    read_status: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否已读"
    )
    read_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="阅读时间")
