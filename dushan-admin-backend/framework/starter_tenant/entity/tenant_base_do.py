from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_database.model.base_do import BaseDO


class TenantBaseDO(BaseDO):
    """共享表中的租户数据基类；具体子类由应用注册器按继承关系识别。

    tenant_id 取租户主键雪花 ID 的字符串形式，定长 19 位，因此列宽取 32 而不是
    传输层 IdentityId 允许的 256——每张租户表都要建 (tenant_id, …) 复合索引，
    utf8mb4 下按 256 字符计为 1024 字节。DB 列比传输层上限更严格是有意为之。
    """

    __abstract__ = True
    tenant_id: Mapped[str] = mapped_column(String(32), nullable=False)
