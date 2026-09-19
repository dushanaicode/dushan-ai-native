from sqlalchemy import select

from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_excel.public import (
    NameProvider,
)
from module_system.dal.dataobject.dept.dept_do import DeptDO
from module_system.dal.mapper.dept.dept_mapper import DeptMapper


@service
class DeptInfoProviderAdapter(NameProvider):
    mapper: DeptMapper = Inject()

    async def names(self, ids):
        return {entry.id: entry.name for entry in await self.mapper.select_by_ids(ids)}

    async def ids(self, names):
        result = await self.mapper.read(select(DeptDO).where(DeptDO.name.in_(names)))
        entries = result.scalars().all()
        resolved = {entry.name: entry.id for entry in entries}
        if len(resolved) != len(entries):
            raise ValueError("名称重复，不能唯一确定部门或岗位")
        return resolved
