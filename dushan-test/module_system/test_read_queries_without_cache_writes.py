from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.core.cache_load_through_coordinator import CacheLoadThroughCoordinator
from framework.starter_di.context.application_context import ApplicationContext
from module_system.controller.admin.user.user_profile_controller import UserProfileController
from module_system.dal.dataobject.permission.role_do import RoleDO
from module_system.dal.dataobject.tenant.tenant_package_do import TenantPackageDO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.service.permission.role_service_impl import RoleServiceImpl
from module_system.service.tenant.tenant_package_service_impl import TenantPackageServiceImpl

pytestmark = pytest.mark.unit


@pytest.fixture
def cold_cache(monkeypatch):
    """运行真实缓存装饰器回源分支，记录 generation 与发布写入。"""
    handler = SimpleNamespace(
        build_full_key=Mock(return_value="test:read-query"),
        capture_generation=AsyncMock(return_value="generation"),
        publish_loaded_value=AsyncMock(),
    )

    async def get_or_load(**kwargs):
        return await kwargs["load_and_publish"]()

    components = {
        CacheHandler: handler,
        CacheLoadThroughCoordinator: SimpleNamespace(get_or_load=get_or_load),
    }
    monkeypatch.setattr(
        ApplicationContext, "lookup", classmethod(lambda cls, kind: components[kind])
    )
    return handler


def audit_fields():
    return {
        "creator": "1",
        "updater": "1",
        "create_time": datetime(2026, 1, 1),
        "update_time": datetime(2026, 1, 1),
        "deleted": False,
    }


@pytest.mark.parametrize("role_code", ["readonly", "common", "super_admin"])
async def test_profile_reads_role_projection_without_cache_writes(cold_cache, role_code):
    role = RoleDO(
        id=2,
        tenant_id="1",
        name="展示角色",
        code=role_code,
        sort=1,
        data_scope=1,
        data_scope_dept_ids=[],
        builtin=2,
        status=1,
        remark=None,
        active_key=0,
        **audit_fields(),
    )
    roles = RoleServiceImpl()
    roles.role_mapper = SimpleNamespace(
        select_by_id=AsyncMock(return_value=role), select_by_ids=AsyncMock(return_value=[role])
    )
    user = AdminUserDO(
        id=1,
        username="visitor",
        nickname="访客",
        tenant_id="1",
        dept_id=None,
        post_ids=[],
        login_ip="127.0.0.1",
        login_date=datetime(2026, 1, 1),
        **audit_fields(),
    )
    response = await UserProfileController.get_user_profile(
        user_service=SimpleNamespace(get_user=AsyncMock(return_value=user)),
        dept_service=SimpleNamespace(),
        post_service=SimpleNamespace(),
        permission_service=SimpleNamespace(
            get_user_role_id_list_by_user_id=AsyncMock(return_value=[2])
        ),
        role_service=roles,
        profile_service=SimpleNamespace(get_user_profile=AsyncMock(return_value=None)),
        security=SimpleNamespace(require=lambda: SimpleNamespace(account_id="1")),
    )
    assert response.data.roles[0].name == "展示角色"
    assert response.data.nickname == "访客"
    cold_cache.capture_generation.assert_not_awaited()
    cold_cache.publish_loaded_value.assert_not_awaited()
    roles.role_mapper.select_by_ids.assert_awaited_once_with([2])


def package_service(exists=True):
    row = TenantPackageDO(
        id=3,
        name="普通套餐",
        status=1,
        remark=None,
        menu_ids=[4],
        quota_config=None,
        **audit_fields(),
    )
    service = TenantPackageServiceImpl()
    service.tenant_package_mapper = SimpleNamespace(
        select_by_id=AsyncMock(return_value=row if exists else None)
    )
    return service


@pytest.mark.parametrize("exists", [True, False])
async def test_package_read_does_not_create_cache_generation_or_publish(cold_cache, exists):
    service = package_service(exists)
    result = await service.get_tenant_package(3)
    assert (result.name if result else None) == ("普通套餐" if exists else None)
    service.tenant_package_mapper.select_by_id.assert_awaited_once_with(3)
    cold_cache.capture_generation.assert_not_awaited()
    cold_cache.publish_loaded_value.assert_not_awaited()


async def test_package_validation_retains_its_internal_cache(cold_cache):
    result = await package_service().valid_tenant_package(3)
    assert result.name == "普通套餐"
    cold_cache.capture_generation.assert_awaited_once()
    cold_cache.publish_loaded_value.assert_awaited_once()
