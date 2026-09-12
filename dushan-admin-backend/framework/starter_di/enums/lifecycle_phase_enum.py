from framework.common.enums.base_enum import BaseEnum


class LifecyclePhaseEnum(BaseEnum):
    """实例初始化与销毁标记。"""

    INITIALIZE = ("post_construct", "初始化")
    DESTROY = ("pre_destroy", "销毁")
