from framework.common.enums.base_enum import BaseEnum


class MenuTypeEnum(BaseEnum):
    DIR = (1, "目录")
    MENU = (2, "菜单")
    BUTTON = (3, "按钮")
    DATA = (4, "数据")
