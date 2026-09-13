from framework.starter_excel.spi.dict_data_provider import DictDataProvider


class DictFrameworkService:
    """字典查询与缓存优化分离；每次查询调用真实 Provider，不隐藏失败。"""

    def __init__(self, provider: DictDataProvider) -> None:
        self._provider = provider

    async def items(self, dict_type: str) -> dict[str, str]:
        """读取独立字典快照，并拒绝无法唯一反向转换的重名标签。"""
        items = dict(await self._provider.items(dict_type))
        if len(set(items.values())) != len(items):
            raise ValueError("字典标签重复，无法唯一反向转换")
        return items

    async def label(self, dict_type: str, value: str) -> str | None:
        """未知编码返回 None，Provider 故障保留原始异常。"""
        return (await self.items(dict_type)).get(value)

    async def value(self, dict_type: str, label: str) -> str | None:
        """未知标签返回 None。"""
        return {label: value for value, label in (await self.items(dict_type)).items()}.get(label)
