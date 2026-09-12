from framework.common.enums.base_enum import BaseEnum


class ComponentTypeEnum(BaseEnum):
    """已支持的定义类别；通用组件只被发现，不自动创建实例。"""

    COMPONENT = ("component", "通用组件")
    ERROR_CODE = ("error_code", "错误码定义")
    CONFIG_MODEL = ("config_model", "配置模型")
