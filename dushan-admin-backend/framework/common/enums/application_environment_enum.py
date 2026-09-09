"""应用运行环境。"""

from enum import StrEnum


class ApplicationEnvironmentEnum(StrEnum):
    """限制配置环境名称，避免把任意路径当作环境文件名。"""

    DEVELOPMENT = "dev"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "prod"
