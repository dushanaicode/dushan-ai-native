from collections.abc import Mapping
from typing import Protocol, runtime_checkable


@runtime_checkable
class DictDataProvider(Protocol):
    """业务侧按字典类型提供编码到显示名称的快照；编码和名称均为字符串。"""

    async def items(self, dict_type: str) -> Mapping[str, str]: ...
