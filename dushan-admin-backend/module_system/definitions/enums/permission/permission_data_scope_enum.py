from framework.common.enums.base_enum import BaseEnum


class PermissionDataScopeEnum(BaseEnum):
    ALL = (1, "全部数据权限")
    DEPT_CUSTOM = (2, "指定部门数据权限")
    DEPT_ONLY = (3, "部门数据权限")
    DEPT_AND_CHILD = (4, "部门及以下数据权限")
    SELF = (5, "仅本人数据权限")

    @classmethod
    def get_name(cls, code: int) -> str:
        return next((item.label for item in cls if item.code == code), "未知")
