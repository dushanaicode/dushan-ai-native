from module_infra.definitions.enums.config.boolean_string_enum import BooleanStringEnum


class BooleanConverter:
    async def to_excel(self, value, context):
        return BooleanStringEnum.YES.label if value else BooleanStringEnum.NO.label

    async def to_python(self, value, context):
        member = BooleanStringEnum.get_by_label(value)
        if member is None:
            raise ValueError("布尔标签不存在")
        return member is BooleanStringEnum.YES

    async def options(self, context):
        return tuple(member.label for member in BooleanStringEnum)
