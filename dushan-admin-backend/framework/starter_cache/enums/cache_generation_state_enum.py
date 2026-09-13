from framework.common.enums.base_enum import BaseEnum


class CacheGenerationStateEnum(BaseEnum):
    """缓存失效 generation 的发布状态；ACTIVE 期间不接受任何回源发布。"""

    ACTIVE = ("active", "失效执行中")
    FINALIZED = ("finalized", "失效已完成")
