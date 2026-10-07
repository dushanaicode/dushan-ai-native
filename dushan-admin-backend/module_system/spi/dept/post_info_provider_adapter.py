from collections.abc import Mapping, Sequence
from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_excel.public import (
    NameProvider,
)
from module_system.service.dept.post_service import PostService


@service
class PostInfoProviderAdapter(NameProvider):
    delegate: PostService = Inject()

    @override
    async def names(self, ids: Sequence[int]) -> Mapping[int, str]:
        """委派岗位服务批量读取名称。"""
        return await self.delegate.get_post_names_by_ids(ids)

    @override
    async def ids(self, names: Sequence[str]) -> Mapping[str, int]:
        """委派岗位服务解析名称并校验歧义。"""
        return await self.delegate.get_post_ids_by_names(names)
