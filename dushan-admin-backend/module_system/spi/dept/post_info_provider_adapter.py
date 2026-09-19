from sqlalchemy import select

from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_excel.public import (
    NameProvider,
)
from module_system.dal.dataobject.dept.post_do import PostDO
from module_system.dal.mapper.dept.post_mapper import PostMapper


@service
class PostInfoProviderAdapter(NameProvider):
    mapper: PostMapper = Inject()

    async def names(self, ids):
        return {entry.id: entry.name for entry in await self.mapper.select_by_ids(ids)}

    async def ids(self, names):
        result = await self.mapper.read(select(PostDO).where(PostDO.name.in_(names)))
        entries = result.scalars().all()
        resolved = {entry.name: entry.id for entry in entries}
        if len(resolved) != len(entries):
            raise ValueError("名称重复，不能唯一确定部门或岗位")
        return resolved
