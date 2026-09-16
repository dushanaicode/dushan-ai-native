from framework.common.enums.base_enum import BaseEnum


class DataScope(BaseEnum):
    """角色范围编码；多个角色取并集，有有效角色时包含本人。"""

    ALL = (1, "全部数据权限")
    DEPT_CUSTOM = (2, "指定部门数据权限")
    DEPT_ONLY = (3, "部门数据权限")
    DEPT_AND_CHILD = (4, "部门及以下数据权限")
    SELF = (5, "仅本人数据权限")
