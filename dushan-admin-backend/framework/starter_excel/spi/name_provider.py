from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class NameProvider(Protocol):
    """部门、岗位分别绑定实例；重名必须由业务 Provider 拒绝，不能任取一项。"""

    async def names(self, ids: Sequence[int]) -> Mapping[int, str]: ...

    async def ids(self, names: Sequence[str]) -> Mapping[str, int]: ...
