from datetime import datetime

from sqlalchemy import DateTime, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from framework.common.enums.status_enum import StatusEnum
from framework.starter_tenant.decorators.tenant_model import global_model
from framework.starter_tenant.entity.global_control_do import GlobalControlDO


@global_model
class DictTypeDO(GlobalControlDO):
    __tablename__ = "system_dict_type"
    __table_args__ = ({**GlobalControlDO.__table_args__, **{"comment": "字典类型表"}},)

    name: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="字典名称")
    type: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="字典类型")
    status: Mapped[int] = mapped_column(
        SmallInteger, default=StatusEnum.ENABLE.code, comment="开启状态（1-启用，0-禁用）"
    )
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="备注")
    deleted_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="删除时间"
    )
