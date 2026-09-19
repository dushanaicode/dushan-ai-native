from framework.common.enums.base_enum import BaseEnum


class CacheNamespace(BaseEnum):
    """缓存键归属的隔离范围。"""

    GLOBAL = ("global", "全局")
    TENANT = ("tenant", "租户")
