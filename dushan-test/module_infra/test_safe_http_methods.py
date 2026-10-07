from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from framework.common.exception import GlobalErrorCodeConstants, ServiceException
from framework.starter_security.core.security_service import SecurityService
from framework.starter_security.definitions.enums.tenant_access_mode import TenantAccessMode
from framework.starter_security.public import PermissionSnapshot, SecurityRealm
from framework.starter_web.public import RoutePolicy
from module_infra.controller.admin.file.file_config_controller import (
    FileConfigController,
    file_config_controller,
)
from module_infra.framework.file.core.client.local.local_file_client import LocalFileClient
from module_infra.framework.file.core.client.local.local_file_client_config import (
    LocalFileClientConfig,
)
from module_infra.service.file.file_config_service_impl import FileConfigServiceImpl
from module_system.controller.admin.auth.auth_controller import auth_controller
from module_system.spi.auth.system_request_access_provider import SystemRequestAccessProvider

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "router,prefix,path",
    [
        (file_config_controller, "/admin-api/infra", "/file/config/test"),
        (auth_controller, "/admin-api/system", "/auth/social-auth-redirect"),
    ],
)
async def test_side_effecting_routes_reject_get(router, prefix, path):
    methods = {method for route in router.routes if route.path == path for method in route.methods}
    assert methods == {"POST"}
    app = FastAPI()
    app.include_router(router, prefix=prefix)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(prefix + path)
    assert response.status_code == 405
    assert response.headers["allow"] == "POST"


def test_social_callback_accepts_both_oauth_response_modes():
    """OAuth 回调按协议支持查询参数（GET）与 form_post（POST）两种方式。"""
    methods = {
        method
        for route in auth_controller.routes
        if route.path == "/auth/social-callback"
        for method in route.methods
    }
    assert methods == {"GET", "POST"}


def file_test_access(roles):
    service = object.__new__(SecurityService)
    service._request_access = SystemRequestAccessProvider()
    service._tenant = SimpleNamespace(is_ready=True)
    service.settings = SimpleNamespace(default_domain="admin", domains=["admin"])
    service._snapshot = AsyncMock(
        return_value=PermissionSnapshot(
            binding="account",
            revision="1",
            permissions=frozenset({"infra:file:config:update"}),
            roles=frozenset(roles),
        )
    )
    session = SimpleNamespace(
        realm=SecurityRealm.TENANT,
        tenant_id="1",
        access_mode=TenantAccessMode.DIRECT_MEMBERSHIP,
        scopes=frozenset(),
        effective_capabilities=frozenset(),
    )
    route = next(
        route
        for route in file_config_controller.routes
        if route.endpoint is FileConfigController.test_file_config
    )
    request = Request(
        {
            "type": "http",
            "method": next(iter(route.methods)),
            "path": "/admin-api/infra/file/config/test",
            "headers": [],
        }
    )
    return service, session, getattr(route.endpoint, RoutePolicy.ATTRIBUTE), request


@pytest.mark.parametrize("roles", [{"readonly", "file_manager"}, {"readonly", "super_admin"}])
async def test_file_probe_rejects_readonly_before_storage_write(roles):
    service, session, policy, request = file_test_access(roles)
    storage = SimpleNamespace(
        upload=AsyncMock(return_value="https://storage.test/probe"),
        get_content=AsyncMock(return_value=b"dushan storage connection test"),
        delete=AsyncMock(),
    )
    probe = SimpleNamespace(get_file_client=AsyncMock(return_value=storage))
    with pytest.raises(ServiceException) as error:
        await service._check_policy(session, policy, request=request)
        await FileConfigServiceImpl.test_file_config(probe, 1)
    assert error.value.error_code == GlobalErrorCodeConstants.DEMO_DENY
    probe.get_file_client.assert_not_awaited()
    storage.upload.assert_not_awaited()
    storage.delete.assert_not_awaited()


@pytest.mark.parametrize("roles", [{"file_manager"}, {"super_admin"}, {"common"}])
async def test_file_probe_remains_available_to_authorized_accounts(roles):
    service, session, policy, request = file_test_access(roles)
    storage = SimpleNamespace(
        upload=AsyncMock(return_value="https://storage.test/probe"),
        get_content=AsyncMock(return_value=b"dushan storage connection test"),
        delete=AsyncMock(),
    )
    await service._check_policy(session, policy, request=request)
    probe = SimpleNamespace(get_file_client=AsyncMock(return_value=storage))
    assert await FileConfigServiceImpl.test_file_config(probe, 1) == "https://storage.test/probe"
    storage.upload.assert_awaited_once()
    storage.get_content.assert_awaited_once()
    storage.delete.assert_awaited_once()


async def test_local_read_initialization_does_not_create_storage(tmp_path):
    path = tmp_path / "uncreated-storage"
    client = LocalFileClient(
        1, LocalFileClientConfig(base_path=str(path), domain="https://storage.test")
    )
    await client.init()
    assert not path.exists()
    with pytest.raises(FileNotFoundError):
        await client.get_content("missing.txt")
    assert not path.exists()


async def test_local_upload_creates_storage_on_the_write_path(tmp_path):
    path = tmp_path / "new-storage"
    client = LocalFileClient(
        1, LocalFileClientConfig(base_path=str(path), domain="https://storage.test")
    )
    await client.init()
    await client.upload("nested/probe.txt", b"content")
    assert await client.get_content("nested/probe.txt") == b"content"
    await client.delete("nested/probe.txt")
    assert not (path / "nested/probe.txt").exists()


async def test_empty_local_listing_does_not_create_storage(tmp_path):
    path = tmp_path / "uncreated-storage"
    client = LocalFileClient(
        1, LocalFileClientConfig(base_path=str(path), domain="https://storage.test")
    )
    await client.init()
    assert await client.list_objects() == {
        "files": [],
        "directories": [],
        "isTruncated": False,
        "nextMarker": "",
    }
    assert not path.exists()
