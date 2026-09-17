from framework.common.enums.base_enum import BaseEnum


class NoticePushStatusEnum(BaseEnum):
    """通知推送状态枚举"""

    PUSHING = (0, "推送中")
    ALL_SUCCESS = (1, "全部成功")
    PARTIAL_FAIL = (2, "部分失败")
    ALL_FAILED = (3, "全部失败")
