from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from framework.starter_ip.model.ip_location import IpLocation
from module_system.controller.admin.area.area_controller import AreaController
from module_system.controller.admin.area.vo.ip_req_vo import IpReqVO


@pytest.mark.parametrize("location, expected", [("地区", "地区"), (None, "未知")])
async def test_area_endpoint_uses_lookup_and_returns_text(location, expected):
    service = SimpleNamespace(
        lookup=AsyncMock(
            return_value=IpLocation("1.2.3.4", "found" if location else "unknown", location)
        )
    )
    result = await AreaController.get_area_by_ip(IpReqVO(ip="1.2.3.4"), service)
    assert result.data == expected
    service.lookup.assert_awaited_once_with("1.2.3.4")


@pytest.mark.parametrize("ip", ["", "invalid", "fe80::1%eth0"])
def test_area_request_rejects_invalid_addresses_before_service(ip):
    with pytest.raises(ValidationError):
        IpReqVO(ip=ip)


def test_area_request_uses_existing_normalization_contract():
    assert IpReqVO(ip=" ::ffff:1.2.3.4 ").ip == "1.2.3.4"
