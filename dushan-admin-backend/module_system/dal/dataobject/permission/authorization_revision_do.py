from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.decorators.tenant_model import global_model
from framework.starter_tenant.entity.global_control_do import GlobalControlDO


@global_model
class AuthorizationRevisionDO(GlobalControlDO):
    """权限元数据版本，与权限变更在同一事务提交；初始 SQL 创建 id=1。"""

    __tablename__ = "system_authorization_revision"
    __table_args__ = {**GlobalControlDO.__table_args__, "comment": "系统授权版本"}
    revision: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
