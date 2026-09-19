from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.service.dept.post_service import PostService


@service
class PostParseFunction:
    NAME = "get_post_by_id"
    delegate: PostService = Inject()

    async def apply(self, value):
        if value is None:
            return ""
        item = await self.delegate.get_post(int(value))
        return "" if item is None else item.name
