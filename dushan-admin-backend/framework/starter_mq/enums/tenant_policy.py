from framework.common.enums.base_enum import BaseEnum


class TenantPolicy(BaseEnum):
    """消费定义对租户上下文的要求。"""

    REQUIRED = ("required", "必须携带租户")
    GLOBAL = ("global", "全局无租户")
    ALLOW_UNAVAILABLE = ("allow_unavailable", "允许租户不可用")
