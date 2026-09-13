from dataclasses import dataclass

from framework.starter_excel.model.conversion_context import ConversionContext
from framework.starter_excel.service.dict_framework_service import DictFrameworkService


@dataclass(frozen=True)
class DictConverter:
    """字典编码与标签双向转换，同一操作中每种字典只查询一次。"""

    dict_type: str

    async def _maps(self, context: ConversionContext) -> tuple[dict[str, str], dict[str, str]]:
        key = ("dictionary", self.dict_type)
        if key not in context.lookups:
            provider = context.providers.dictionaries
            if provider is None:
                raise ValueError("未提供字典 Provider")
            items = await DictFrameworkService(provider).items(self.dict_type)
            context.lookups[key] = items, {label: code for code, label in items.items()}
        return context.lookups[key]

    async def to_excel(self, value: str | int, context: ConversionContext) -> str:
        items, _ = await self._maps(context)
        if type(value) not in (str, int) or str(value) not in items:
            raise ValueError("字典编码不存在")
        return items[str(value)]

    async def to_python(self, value: str, context: ConversionContext) -> str:
        _, reverse = await self._maps(context)
        if value not in reverse:
            raise ValueError("字典标签不存在")
        return reverse[value]

    async def options(self, context: ConversionContext) -> tuple[str, ...]:
        items, _ = await self._maps(context)
        return tuple(items.values())
