from sqlalchemy import JSON, BigInteger, Index, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.public import (
    TenantBaseDO,
)
from module_system.definitions.enums.notification.notice_push_status_enum import (
    NoticePushStatusEnum,
)


class NoticeLogDO(TenantBaseDO):
    __tablename__ = "system_notification_notice_log"
    __table_args__ = (
        Index("ix_system_notification_notice_log_tenant", "tenant_id"),
        {**TenantBaseDO.__table_args__, **{"comment": "通知日志表"}},
    )

    notice_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="关联的通知编号")
    notice_title: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="通知标题(冗余快照)"
    )
    notice_type: Mapped[int] = mapped_column(Integer, nullable=False, comment="通知类型(冗余快照)")
    push_target_type: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        comment="推送目标类型(NoticePushTargetTypeEnum): 1=按用户, 2=按部门, 3=混合",
    )
    target_user_ids: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=None, comment="目标用户ID列表(原始选择)"
    )
    target_dept_ids: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=None, comment="目标部门ID列表(原始选择)"
    )
    target_dept_names: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=None, comment="目标部门名称列表(冗余快照)"
    )
    push_channels: Mapped[list] = mapped_column(JSON, nullable=False, comment="推送渠道")
    total_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="推送总人数"
    )
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="成功数")
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="失败数")
    push_status: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=NoticePushStatusEnum.PUSHING.code,
        comment="推送状态(NoticePushStatusEnum): 0=推送中, 1=全部成功, 2=部分失败, 3=全部失败",
    )
    publisher_info: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=None, comment="发布者信息"
    )
