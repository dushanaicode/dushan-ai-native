from framework.common.enums.base_enum import BaseEnum


class PermissionTypeEnum(BaseEnum):
    """权限规则中使用的操作类型。"""

    QUERY = (1, "查询")
    LIST = (2, "列表")
    CREATE = (3, "新增")
    UPDATE = (4, "修改")
    DELETE = (5, "删除")
    EXPORT = (6, "导出")
    EXECUTE = (7, "执行")
