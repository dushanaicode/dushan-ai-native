from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.entity.tenant_base_do import TenantBaseDO


class SmsCodeDO(TenantBaseDO):
    __tablename__ = "system_sms_code"
    __table_args__ = (
        Index("ix_system_sms_code_tenant", "tenant_id"),
        {**TenantBaseDO.__table_args__, **{"comment": "手机验证码表"}},
    )

    mobile: Mapped[str] = mapped_column(String(11), nullable=False, comment="手机号")
    code: Mapped[str] = mapped_column(String(6), nullable=False, comment="验证码")
    create_ip: Mapped[str] = mapped_column(String(15), nullable=False, comment="创建 IP")
    scene: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="发送场景")
    today_index: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="今日发送的第几条"
    )
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="是否使用")
    used_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="使用时间")
    used_ip: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="使用 IP")
