import json

from framework.starter_di.decorators.components import framework
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_ip.client.ip_location_http_client import IpLocationHttpClient
from framework.starter_ip.config.ip_settings import IpSettings
from framework.starter_ip.core.client_ip_resolver import ClientIpResolver
from framework.starter_ip.exception.ip_provider_error import IpProviderError
from framework.starter_ip.spi.ip_location_provider import IpLocationProvider


@framework(providers=(IpLocationProvider,), scope=ComponentScopeEnum.SINGLETON)
class PconlineIpLocationProvider(IpLocationProvider):
    name = "pconline"
    online = True

    def __init__(self, settings: IpSettings, client: IpLocationHttpClient) -> None:
        self._settings, self._client = settings, client

    async def query(self, ip: str, remaining_seconds: float) -> str | None:
        content = await self._client.get(
            self.name,
            self._settings.pconline_api_url,
            params={"ip": ip, "json": "true"},
            timeout_seconds=remaining_seconds,
        )
        try:
            data = json.loads(content.decode("gbk"))
            if not isinstance(data, dict) or any(
                type(data.get(key)) is not str for key in ("ip", "pro", "city", "err")
            ):
                raise ValueError("PConline 必需字段无效")
            if ClientIpResolver.normalize_ip(data["ip"]) != ip:
                raise ValueError("PConline IP 回显不一致")
            province, city = (
                data["pro"].strip().removesuffix("省"),
                data["city"].strip().removesuffix("市"),
            )
            if data["err"] == "noprovince" and not province and not city:
                return None
            if data["err"] == "nocity" and province and not city:
                return province
            if data["err"] != "" or not (province or city):
                raise ValueError("PConline 结果状态不一致")
            return "-".join(part for part in (province, city) if part)
        except (ValueError, UnicodeError) as error:
            raise IpProviderError(self.name, "protocol") from error
