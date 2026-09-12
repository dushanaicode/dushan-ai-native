from framework.common.enums.base_enum import BaseEnum


class ExecutionPhaseEnum(BaseEnum):
    """区分业务和内部初始化/清理，阶段许可随其有效区间结束而撤销。"""

    BUSINESS = ("business", "业务执行")
    INITIALIZE = ("initialize", "内部初始化")
    CLEANUP = ("cleanup", "内部清理")
