from sqlalchemy import BigInteger, Boolean, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from framework.common.enums import StatusEnum
from framework.starter_tenant.public import (
    GlobalControlDO,
    global_model,
)


@global_model
class MenuDO(GlobalControlDO):
    __tablename__ = "system_menu"
    __table_args__ = ({**GlobalControlDO.__table_args__, **{"comment": "菜单权限表"}},)

    # 根节点 ID 常量
    ID_ROOT = 0

    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="菜单名称")
    permission: Mapped[str] = mapped_column(
        String(100), nullable=False, default="", comment="权限标识"
    )
    kind: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="菜单种类：group/page/action/link/iframe"
    )
    data_permission: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否为数据权限操作，承接源 DATA 类型"
    )
    url: Mapped[str | None] = mapped_column(
        String(2048), nullable=True, comment="外链或内嵌页面地址"
    )
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="显示顺序")
    parent_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, comment="父菜单ID"
    )
    path: Mapped[str] = mapped_column(String(200), default="", comment="路由地址")
    icon: Mapped[str] = mapped_column(String(100), default="#", comment="菜单图标")
    component: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="组件路径")
    component_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="组件名")
    status: Mapped[int] = mapped_column(
        SmallInteger, default=StatusEnum.ENABLE.code, comment="开启状态（1-启用，0-禁用）"
    )
    visible: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否可见")
    keep_alive: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否缓存")
    always_show: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否总是显示")
