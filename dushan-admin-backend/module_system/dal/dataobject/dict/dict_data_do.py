from sqlalchemy import JSON, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from framework.common.enums import StatusEnum
from framework.starter_tenant.public import (
    GlobalControlDO,
    global_model,
)


@global_model
class DictDataDO(GlobalControlDO):
    __tablename__ = "system_dict_data"
    __table_args__ = ({**GlobalControlDO.__table_args__, **{"comment": "字典数据表"}},)

    sort: Mapped[int] = mapped_column(Integer, default=0, comment="字典排序")
    label: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="字典标签")
    value: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="字典键值")
    dict_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="", comment="字典类型"
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, default=StatusEnum.ENABLE.code, comment="开启状态（1-启用，0-禁用）"
    )
    color_type: Mapped[str | None] = mapped_column(String(100), default="", comment="颜色类型")
    tag_style: Mapped[dict | str | None] = mapped_column(JSON, default="", comment="按钮样式")
    permission: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        comment="权限标识（该选项所需的权限码，NULL表示无需权限）",
    )
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="备注")
