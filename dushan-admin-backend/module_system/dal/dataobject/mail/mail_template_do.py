from sqlalchemy import JSON, BigInteger, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from framework.common.enums import StatusEnum
from framework.starter_tenant.public import (
    GlobalControlDO,
    global_model,
)


@global_model
class MailTemplateDO(GlobalControlDO):
    __tablename__ = "system_mail_template"
    __table_args__ = ({**GlobalControlDO.__table_args__, **{"comment": "邮件模版表"}},)

    name: Mapped[str] = mapped_column(String(63), nullable=False, comment="模板名称")
    code: Mapped[str] = mapped_column(String(63), nullable=False, comment="模板编码")
    account_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="发送的邮箱账号编号"
    )
    nickname: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="发送人名称")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="模板标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="模板内容")
    params: Mapped[list[str]] = mapped_column(JSON, nullable=False, comment="参数数组")
    status: Mapped[int] = mapped_column(
        SmallInteger, default=StatusEnum.ENABLE.code, comment="开启状态（1-启用，0-禁用）"
    )
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="备注")
