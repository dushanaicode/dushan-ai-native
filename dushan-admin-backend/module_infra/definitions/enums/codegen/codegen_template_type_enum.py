from framework.common.enums import BaseEnum


class CodegenTemplateTypeEnum(BaseEnum):
    """代码生成 - 模板类型枚举"""

    CRUD = (1, "基础 CRUD")
    TREE = (2, "树形 CRUD")
    SUB = (15, "主子表 CRUD")
