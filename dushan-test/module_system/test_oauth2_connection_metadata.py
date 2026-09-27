from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from starlette.requests import HTTPConnection

from framework.common.enums import UserTypeEnum
from framework.starter_ip.public import IpLocation
from framework.starter_web.public import RequestContext
from module_system.service.oauth2.oauth2_token_service_impl import OAuth2TokenServiceImpl


@pytest.mark.parametrize("renewal", [False, True])
@pytest.mark.parametrize("ip_enabled", [False, True])
async def test_issued_admin_token_records_request_connection_on_login_and_refresh(
    renewal, ip_enabled
):
    service = OAuth2TokenServiceImpl()
    service.settings = SimpleNamespace(application_id="test", default_domain="admin")
    service.tenant = SimpleNamespace(get_required_tenant_id=lambda: "1")
    service.database = SimpleNamespace(after_commit=Mock())
    service.cache = SimpleNamespace(cache_token=AsyncMock())
    service.ip_settings = SimpleNamespace(enabled=ip_enabled)
    service.ip_locations = SimpleNamespace(
        lookup=AsyncMock(return_value=IpLocation("127.0.0.1", "loopback", "回环地址"))
    )

    async def insert(row):
        row.id = 123

    service.refresh_tokens = SimpleNamespace(insert=AsyncMock(side_effect=insert))
    service.access_tokens = SimpleNamespace(insert=AsyncMock(side_effect=insert))
    agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    connection = HTTPConnection(
        {
            "type": "http",
            "headers": [(b"user-agent", agent.encode()), (b"x-forwarded-for", b"1.2.3.4")],
        }
    )
    expires = (
        datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7) if renewal else None
    )
    client = SimpleNamespace(
        client_id="default",
        access_token_validity_seconds=1800,
        refresh_token_validity_seconds=86400,
    )
    with RequestContext.bind(connection, "test", "127.0.0.1"):
        await service._issue(
            1,
            UserTypeEnum.ADMIN.code,
            client,
            [],
            1,
            {"username": "admin"},
            "family",
            refresh_expires=expires,
        )

    saved = service.access_tokens.insert.call_args.args[0].user_info
    assert saved["username"] == "admin"
    assert saved["ipaddr"] == "127.0.0.1"  # 采用中间件确认的地址，不重新信任转发头。
    assert saved["login_location"] == ("回环地址" if ip_enabled else None)
    if not ip_enabled:
        service.ip_locations.lookup.assert_not_awaited()
    assert saved["user_agent"] == agent
    assert saved["browser"].startswith("Chrome 130")
    assert saved["os"] == "Windows 10"
    if renewal:
        assert service.refresh_tokens.insert.call_args.args[0].expires_time == expires
