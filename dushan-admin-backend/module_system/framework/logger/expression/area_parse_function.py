from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_ip.service.area_service import AreaService


@service
class AreaParseFunction:
    NAME = "get_area"
    areas: AreaService = Inject()

    async def apply(self, value):
        return "" if value is None else self.areas.format_area_path(int(value))
