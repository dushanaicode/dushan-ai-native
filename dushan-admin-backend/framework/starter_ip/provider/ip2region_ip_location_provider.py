from framework.starter_di.decorators.components import framework
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_ip.core.ip2region_database import Ip2RegionDatabase
from framework.starter_ip.exception.ip_error_code_constants import IpErrorCodeConstants
from framework.starter_ip.exception.ip_exception import IpException
from framework.starter_ip.spi.ip_location_provider import IpLocationProvider


@framework(providers=(IpLocationProvider,), scope=ComponentScopeEnum.SINGLETON)
class Ip2RegionIpLocationProvider(IpLocationProvider):
    name = "ip2region"
    online = False

    def __init__(self, database: Ip2RegionDatabase) -> None:
        self._database = database

    async def query(self, ip: str, remaining_seconds: float) -> str | None:
        region = self._database.search(ip)
        if not region:
            return None
        fields = region.split("|")
        if len(fields) != 5 or not all(fields):
            raise IpException(IpErrorCodeConstants.QUERY_FAILED)
        country, province, city, _isp, _iso = ("" if field == "0" else field for field in fields)
        if country == "中国":
            province, city = province.removesuffix("省"), city.removesuffix("市")
            return "-".join(part for part in (province, city) if part) or country
        return "-".join(part for part in (country, province, city) if part) or None
