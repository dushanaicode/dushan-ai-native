from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from framework.common.enums.status_enum import StatusEnum
from framework.starter_tenant.decorators.tenant_model import global_model
from framework.starter_tenant.entity.global_control_do import GlobalControlDO


@global_model
class TenantDO(GlobalControlDO):
    __tablename__ = "system_tenant"
    __table_args__ = ({**GlobalControlDO.__table_args__, **{"comment": "租户"}},)

    # 添加系统租户套餐ID常量，值可以根据实际需求修改
    PACKAGE_ID_SYSTEM = 0

    name: Mapped[str] = mapped_column(String(30), nullable=False, comment="租户名")
    contact_user_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="联系人的用户编号"
    )
    contact_name: Mapped[str] = mapped_column(String(30), nullable=False, comment="联系人")
    contact_mobile: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="联系手机"
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, default=StatusEnum.ENABLE.code, comment="开启状态（1-启用，0-禁用）"
    )
    websites: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="绑定域名列表")
    package_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="租户套餐编号")
    expire_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="过期时间"
    )
    account_count: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="账号数量")
