from importlib.metadata import PackageNotFoundError
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from test_location_service import SampleProvider

from framework.starter_ip.core.ip2region_database import Ip2RegionDatabase
from framework.starter_ip.definitions.constants.ip_error_codes import IpErrorCodes
from framework.starter_ip.exception.ip_exception import IpException
from framework.starter_ip.provider.ip2region_ip_location_provider import Ip2RegionIpLocationProvider
from framework.starter_ip.service.ip_location_service import IpLocationService


@pytest.mark.parametrize("field", ["pconline_api_url", "vore_api_url"])
@pytest.mark.parametrize("port", ["not-a-port", "-1", "65536"])
def test_provider_url_rejects_invalid_ports_at_configuration_boundary(ip_settings, field, port):
    with pytest.raises(ValidationError):
        ip_settings(**{field: f"https://example.com:{port}/api"})


@pytest.mark.parametrize("field", ["pconline_api_url", "vore_api_url"])
def test_provider_url_accepts_explicit_valid_port(ip_settings, field):
    url = "https://example.com:8443/api"
    assert getattr(ip_settings(**{field: url}), field) == url


@pytest.mark.parametrize("reason", ["database", "protocol"])
async def test_local_query_failure_has_context_and_continues_to_online(ip_settings, reason):
    search = Mock(return_value="bad|record")
    if reason == "database":
        search.side_effect = IpException(IpErrorCodes.QUERY_FAILED)
    local = Ip2RegionIpLocationProvider(SimpleNamespace(search=search))
    online = SampleProvider("fallback location")
    service = IpLocationService(
        ip_settings(online_enabled=True, online_providers=["sample"]), [local, online]
    )
    service.open()
    try:
        result = await service.lookup("1.2.3.4")
        assert result.location == "fallback location" and result.provider == "sample"
        assert result.failures == (f"ip2region:{reason}",)
    finally:
        await service.close()


def test_missing_binding_metadata_has_xdb_load_error(monkeypatch):
    monkeypatch.setattr(
        "framework.starter_ip.core.ip2region_database.version",
        Mock(side_effect=PackageNotFoundError("py-ip2region")),
    )
    database = Ip2RegionDatabase()
    with pytest.raises(IpException) as caught:
        database.initialize(("ipv4",))
    assert caught.value.error_code is IpErrorCodes.XDB_LOAD_ERROR
    assert isinstance(caught.value.__cause__, PackageNotFoundError)
    assert database._searchers is None
