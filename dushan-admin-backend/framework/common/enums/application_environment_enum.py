from framework.common.enums.base_enum import BaseEnum


class ApplicationEnvironmentEnum(BaseEnum):
    """配置文件支持的四种运行环境。"""

    DEVELOPMENT = ("dev", "开发环境")
    TEST = ("test", "测试环境")
    STAGING = ("staging", "预发布环境")
    PRODUCTION = ("prod", "生产环境")
