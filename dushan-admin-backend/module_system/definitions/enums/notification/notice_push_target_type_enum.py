from framework.common.enums import BaseEnum


class NoticePushTargetTypeEnum(BaseEnum):
    USER = (1, "按用户")
    DEPT = (2, "按部门")
    MIXED = (3, "混合")
