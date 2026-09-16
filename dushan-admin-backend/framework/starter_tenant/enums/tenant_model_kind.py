from framework.common.enums.base_enum import BaseEnum


class TenantModelKind(BaseEnum):
    """ORM 模型的租户归属声明。"""

    TENANT = ("tenant", "租户数据")
    GLOBAL = ("global", "全局数据")
