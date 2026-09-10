from enum import StrEnum


class ApplicationEnvironmentEnum(StrEnum):
    """配置文件支持的四种运行环境。"""

    DEVELOPMENT = "dev"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "prod"
