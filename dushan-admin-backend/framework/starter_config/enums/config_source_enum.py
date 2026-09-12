from framework.common.enums.base_enum import BaseEnum


class ConfigSourceEnum(BaseEnum):
    """模型配置来源；外部快照由数据库或远程适配器显式提供。"""

    ENVIRONMENT = ("environment", "进程环境")
    MEMORY = ("memory", "运行覆盖")
    EXTERNAL = ("external", "外部快照")
    FILE = ("file", "附加文件")
    YAML = ("yaml", "启动配置")
