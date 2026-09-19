from framework.common.enums import BaseEnum


class DataSourceTypeEnum(BaseEnum):
    """数据源类型枚举"""

    MASTER = (1, "主库")
    SLAVE = (2, "从库")
    BACKUP = (3, "备份库")
