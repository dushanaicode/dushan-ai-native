from framework.common.enums.base_enum import BaseEnum


class DataSourceHealthStatusEnum(BaseEnum):
    """
    健康状态枚举

    用于标识数据源的健康状况
    """

    HEALTHY = (0, "健康")
    WARNING = (1, "警告")
    FAILURE = (2, "故障")
