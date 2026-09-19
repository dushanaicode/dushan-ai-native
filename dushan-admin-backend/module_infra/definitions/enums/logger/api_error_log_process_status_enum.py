from framework.common.enums import BaseEnum


class ApiErrorLogProcessStatusEnum(BaseEnum):
    """API 异常数据的处理状态"""

    INIT = (0, "未处理")
    DONE = (1, "已处理")
    IGNORE = (2, "已忽略")
