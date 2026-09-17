from framework.common.enums.base_enum import BaseEnum


class SmsReceiveStatusEnum(BaseEnum):
    INIT = (0, "初始化")
    SUCCESS = (10, "接收成功")
    FAILURE = (20, "接收失败")
