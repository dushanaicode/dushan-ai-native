from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_ip.public import (
    AreaService,
)


@service
class AreaParseFunction:
    NAME = "get_area"
    areas: AreaService = Inject()

    async def apply(self, value):
        return "" if value is None else self.areas.format_area_path(int(value))
