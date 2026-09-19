from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.public import (
    TenantBaseDO,
)


class AnnouncementDO(TenantBaseDO):
    __tablename__ = "system_announcement"
    __table_args__ = (
        Index("ix_system_announcement_tenant", "tenant_id"),
        {**TenantBaseDO.__table_args__, **{"comment": "公告表"}},
    )

    title: Mapped[str] = mapped_column(String(100), nullable=False, comment="公告标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="公告内容")
    status: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        comment="公告状态（0-草稿，1-待发布，2-已发布，3-已过期）",
    )
    is_top: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否置顶")
    sort: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="排序序号（数值越小越靠前）"
    )
    category: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="公告类别，参见 AnnouncementCategoryEnum"
    )
    publish_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="发布时间"
    )
    expire_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="过期时间"
    )
    publisher: Mapped[str] = mapped_column(String(64), nullable=False, comment="发布人")
