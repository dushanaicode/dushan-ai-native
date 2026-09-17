from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.service.dept.dept_service import DeptService


@service
class DeptParseFunction:
    NAME = "get_dept_by_id"
    delegate: DeptService = Inject()

    async def apply(self, value):
        if value is None:
            return ""
        item = await self.delegate.get_dept(int(value))
        return "" if item is None else item.name
