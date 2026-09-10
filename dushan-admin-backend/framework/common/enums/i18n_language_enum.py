from framework.common.enums.base_enum import BaseEnum


class I18nLanguageEnum(BaseEnum):
    """语言标识，用于选择对应的翻译内容。"""

    ZH_CN = ("zh-CN", "简体中文")
    EN_US = ("en-US", "美式英语")
