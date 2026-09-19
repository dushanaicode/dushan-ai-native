from framework.common.enums import BaseEnum


class MenuKindEnum(BaseEnum):
    GROUP = ("group", "目录")
    PAGE = ("page", "页面")
    ACTION = ("action", "操作")
    LINK = ("link", "外链")
    IFRAME = ("iframe", "内嵌页面")
