from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.decorators.tenant_model import global_model
from framework.starter_tenant.entity.global_control_do import GlobalControlDO


@global_model
class MailAccountDO(GlobalControlDO):
    __tablename__ = "system_mail_account"
    __table_args__ = ({**GlobalControlDO.__table_args__, **{"comment": "邮箱账号表"}},)

    mail: Mapped[str] = mapped_column(String(255), nullable=False, comment="邮箱")
    username: Mapped[str] = mapped_column(String(255), nullable=False, comment="用户名")
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码")
    host: Mapped[str] = mapped_column(String(255), nullable=False, comment="SMTP 服务器域名")
    port: Mapped[int] = mapped_column(Integer, nullable=False, comment="SMTP 服务器端口")
    ssl_enable: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否开启 SSL")
    starttls_enable: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否开启 STARTTLS"
    )
