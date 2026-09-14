from framework.common.enums.base_enum import BaseEnum


class OperateTypeEnum(BaseEnum):
    OTHER = (0, "其他")
    GET = (1, "查询")
    CREATE = (2, "新增")
    UPDATE = (3, "修改")
    DELETE = (4, "删除")
    EXPORT = (5, "导出")
    IMPORT = (6, "导入")

    @classmethod
    def from_method(cls, method: str) -> "OperateTypeEnum":
        return {
            "GET": cls.GET,
            "POST": cls.CREATE,
            "PUT": cls.UPDATE,
            "PATCH": cls.UPDATE,
            "DELETE": cls.DELETE,
        }.get(method, cls.OTHER)
