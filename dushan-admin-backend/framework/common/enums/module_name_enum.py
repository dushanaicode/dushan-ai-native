from framework.common.enums.base_enum import BaseEnum


class ModuleNameEnum(BaseEnum):
    """各模块使用的包路径标识。

    这里只声明名称，是否加载及依赖顺序由模块装配决定。
    """

    SYSTEM = ("module_system", "系统管理")
    INFRA = ("module_infra", "基础设施")
