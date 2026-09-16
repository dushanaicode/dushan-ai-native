from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_database.model.base_do import BaseDO


class TenantBaseDO(BaseDO):
    """共享表中的租户数据基类；具体模型仍显式使用 tenant_model 声明。"""

    __abstract__ = True
    tenant_id: Mapped[str] = mapped_column(String(256), nullable=False)
