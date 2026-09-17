from sqlalchemy import JSON, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from framework.common.enums.status_enum import StatusEnum
from framework.starter_tenant.decorators.tenant_model import global_model
from framework.starter_tenant.entity.global_control_do import GlobalControlDO


@global_model
class TenantPackageDO(GlobalControlDO):
    __tablename__ = "system_tenant_package"
    __table_args__ = ({**GlobalControlDO.__table_args__, **{"comment": "租户套餐"}},)

    name: Mapped[str] = mapped_column(String(30), nullable=False, comment="套餐名")
    status: Mapped[int] = mapped_column(
        SmallInteger, default=StatusEnum.ENABLE.code, comment="开启状态（1-启用，0-禁用）"
    )
    remark: Mapped[str | None] = mapped_column(String(256), nullable=True, comment="备注")
    menu_ids: Mapped[list[int]] = mapped_column(
        JSON, nullable=False, comment="关联的菜单编号 (JSON)"
    )
    quota_config: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="通用配额模板（多模块共享，如 ai / sms / storage）",
    )
