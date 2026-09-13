import ipaddress
import json

from framework.starter_di.decorators.components import framework
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_ip.client.ip_location_http_client import IpLocationHttpClient
from framework.starter_ip.config.ip_settings import IpSettings
from framework.starter_ip.core.client_ip_resolver import ClientIpResolver
from framework.starter_ip.exception.ip_provider_error import IpProviderError
from framework.starter_ip.spi.ip_location_provider import IpLocationProvider


@framework(providers=(IpLocationProvider,), scope=ComponentScopeEnum.SINGLETON)
class VoreIpLocationProvider(IpLocationProvider):
    name = "vore"
    online = True

    def __init__(self, settings: IpSettings, client: IpLocationHttpClient) -> None:
        self._settings, self._client = settings, client

    async def query(self, ip: str, remaining_seconds: float) -> str | None:
        content = await self._client.get(
            self.name,
            self._settings.vore_api_url,
            params={"ip": ip},
            timeout_seconds=remaining_seconds,
        )
        try:
            data = json.loads(content)
            if (
                not isinstance(data, dict)
                or type(data.get("code")) is not int
                or data["code"] != 200
                or data.get("msg") != "SUCCESS"
            ):
                raise ValueError("VORE 状态无效")
            for group, fields in (
                ("ipinfo", ("text", "type")),
                ("adcode", ("p", "c")),
                ("ipdata", ("info1", "info2")),
            ):
                item = data.get(group)
                if not isinstance(item, dict) or any(
                    type(item.get(key)) is not str for key in fields
                ):
                    raise ValueError("VORE 必需字段无效")
            if (
                ClientIpResolver.normalize_ip(data["ipinfo"]["text"]) != ip
                or data["ipinfo"]["type"] != f"ipv{ipaddress.ip_address(ip).version}"
            ):
                raise ValueError("VORE IP 回显不一致")
            province, city = data["adcode"]["p"].strip(), data["adcode"]["c"].strip()
            if not (province or city):
                province = data["ipdata"]["info1"].strip().removesuffix("省")
                city = data["ipdata"]["info2"].strip().removesuffix("市")
            return "-".join(part for part in (province, city) if part) or None
        except (ValueError, UnicodeError) as error:
            raise IpProviderError(self.name, "protocol") from error
