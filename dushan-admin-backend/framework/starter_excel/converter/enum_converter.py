from dataclasses import dataclass

from framework.common.enums.base_enum import BaseEnum
from framework.starter_excel.model.conversion_context import ConversionContext


@dataclass(frozen=True)
class EnumConverter:
    """沿用 Native BaseEnum 的严格编码契约，不把布尔值当作整数编码。"""

    enum_type: type[BaseEnum]

    async def to_excel(self, value: int | str | BaseEnum, context: ConversionContext) -> str:
        return self.enum_type.from_code(value).label

    async def to_python(self, value: str, context: ConversionContext) -> int | str:
        member = self.enum_type.get_by_label(value)
        if member is None:
            raise ValueError("枚举标签不存在")
        return member.code

    async def options(self, context: ConversionContext) -> tuple[str, ...]:
        return tuple(member.label for member in self.enum_type)
