from sqlalchemy import JSON, BigInteger, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from framework.common.enums.builtin_type_enum import BuiltinTypeEnum
from framework.common.enums.status_enum import StatusEnum
from framework.starter_tenant.decorators.tenant_model import global_model
from framework.starter_tenant.entity.global_control_do import GlobalControlDO


@global_model
class SmsTemplateDO(GlobalControlDO):
    __tablename__ = "system_sms_template"
    __table_args__ = ({**GlobalControlDO.__table_args__, **{"comment": "短信模板表"}},)

    type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="短信类型【SmsTemplateTypeEnum】"
    )
    builtin: Mapped[int] = mapped_column(
        SmallInteger,
        default=BuiltinTypeEnum.CUSTOM.code,
        comment="内置类型（1-内置 2-自定义）【BuiltinTypeEnum】",
    )
    status: Mapped[int] = mapped_column(
        SmallInteger,
        default=StatusEnum.ENABLE.code,
        comment="开启状态（1-启用，0-禁用）【StatusEnum】",
    )
    code: Mapped[str] = mapped_column(String(63), nullable=False, comment="模板编码")
    name: Mapped[str] = mapped_column(String(63), nullable=False, comment="模板名称")
    content: Mapped[str] = mapped_column(String(255), nullable=False, comment="模板内容")
    params: Mapped[list[str]] = mapped_column(JSON, nullable=False, comment="参数数组")
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="备注")
    api_template_id: Mapped[str] = mapped_column(
        String(63), nullable=False, comment="短信 API 的模板编号"
    )
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="短信渠道编号")
    channel_code: Mapped[str] = mapped_column(String(63), nullable=False, comment="短信渠道编码")
