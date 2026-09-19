from framework.common.enums.base_enum import BaseEnum


class ComponentScopeEnum(BaseEnum):
    """每次解析新建，或在当前容器中复用唯一实例。"""

    SINGLETON = ("singleton", "单例")
    TRANSIENT = ("transient", "瞬态")
