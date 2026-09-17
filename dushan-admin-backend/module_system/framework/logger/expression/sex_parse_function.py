from framework.starter_di.decorators.components import service
from module_system.definitions.enums.common.common_sex_enum import CommonSexEnum


@service
class SexParseFunction:
    NAME = "get_sex"

    async def apply(self, value):
        return "" if value is None else CommonSexEnum.from_code(value).label
