from framework.common.enums import BaseEnum


class ConfigModuleEnum(BaseEnum):
    """配置所属模块枚举 - 与字典 infra_config_module 保持同步"""

    SYSTEM = ("system", "系统")
    INFRA = ("infra", "基础设施")
    FRAMEWORK = ("framework", "框架")
    AI = ("ai", "AI")
