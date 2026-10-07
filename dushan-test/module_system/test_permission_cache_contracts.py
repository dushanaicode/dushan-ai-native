from functools import partial
from inspect import unwrap
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call

import pytest

from framework.common.exception import ServiceException
from framework.starter_cache.core.cache_load_through_coordinator import CacheLoadThroughCoordinator
from framework.starter_cache.public import CacheHandler
from framework.starter_di.public import ApplicationContext
from module_system.controller.admin.permission.vo.role.role_save_req_vo import RoleSaveReqVO
from module_system.dal.cache.system_cache_key_constants import SystemCacheKeyConstants
from module_system.dal.dataobject.permission.menu_do import MenuDO
from module_system.dal.dataobject.permission.role_do import RoleDO
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.permission.menu_service_impl import MenuServiceImpl
from module_system.service.permission.permission_cache_service_impl import (
    PermissionCacheServiceImpl,
)
from module_system.service.permission.permission_service_impl import PermissionServiceImpl
from module_system.service.permission.role_service_impl import RoleServiceImpl

pytestmark = pytest.mark.unit


@pytest.fixture
def role_service():
    """保留角色与权限服务的实际调用链，仅替换数据库和缓存资源。"""
    cache_service = PermissionCacheServiceImpl()
    cache_service.database = SimpleNamespace(after_commit=Mock())
    cache_service.cache = SimpleNamespace(delete_all=AsyncMock())
    permissions = PermissionServiceImpl()
    permissions.events = cache_service
    permissions.revisions = SimpleNamespace(advance=AsyncMock())
    permissions.role_menu_mapper = SimpleNamespace(delete_list_by_role_id=AsyncMock())
    permissions.user_role_mapper = SimpleNamespace(delete_list_by_role_id=AsyncMock())
    permissions.process_role_deleted = partial(
        unwrap(PermissionServiceImpl.process_role_deleted), permissions
    )
    service = RoleServiceImpl()
    service.permission_cache = cache_service
    service.permission_service = permissions
    service.revisions = SimpleNamespace(advance=AsyncMock())
    service.security_settings = SimpleNamespace(bizlog_enabled=False)
    service.log_context = SimpleNamespace(put=Mock())
    service.role_mapper = SimpleNamespace(update_by_id=AsyncMock(), delete_by_id=AsyncMock())
    service.validate_role_for_update = AsyncMock(
        side_effect=lambda role_id: RoleDO(
            id=role_id, name="原角色", code="test", sort=1, remark=None
        )
    )
    service.validate_role_duplicate = AsyncMock()
    service.delete_role = partial(unwrap(RoleServiceImpl.delete_role), service)
    return service


async def assert_invalidation_after_commit(service, expected_count):
    """提交前不清缓存，每次登记均完整覆盖角色权限所需的三个键。"""
    cache_service = service.permission_cache
    cache_service.cache.delete_all.assert_not_awaited()
    registrations = cache_service.database.after_commit.call_args_list
    assert len(registrations) == expected_count
    for registration in registrations:
        assert registration.kwargs == {"required": True, "name": "system-permissions"}
        (callback,) = registration.args
        await callback()
    assert (
        cache_service.cache.delete_all.await_args_list
        == [
            call(SystemCacheKeyConstants.USER_ROLE_ID_LIST),
            call(SystemCacheKeyConstants.MENU_ROLE_ID_LIST),
            call(SystemCacheKeyConstants.ROLE),
        ]
        * expected_count
    )


@pytest.mark.parametrize(
    ("method", "args"),
    [
        (
            "update_role",
            (RoleSaveReqVO(id="7", name="新角色", code="test", sort=1),),
        ),
        ("update_role_data_scope", (7, 2, {10, 11})),
        ("update_role_status", (7, 1)),
    ],
)
async def test_role_update_registers_one_complete_invalidation(role_service, method, args):
    """角色三种修改只登记统一失效，避免重复推进 ROLE generation。"""
    await unwrap(getattr(RoleServiceImpl, method))(role_service, *args)
    role_service.validate_role_for_update.assert_awaited_once_with(7)
    role_service.role_mapper.update_by_id.assert_awaited_once()
    await assert_invalidation_after_commit(role_service, 1)


async def test_role_delete_reuses_relation_cleanup_invalidation(role_service):
    """单删保留关系清理和日志，并复用清理服务的唯一失效登记。"""
    role_service.security_settings.bizlog_enabled = True
    await role_service.delete_role(7)
    role_service.role_mapper.delete_by_id.assert_awaited_once_with(7)
    role_service.permission_service.role_menu_mapper.delete_list_by_role_id.assert_awaited_once_with(
        7
    )
    role_service.permission_service.user_role_mapper.delete_list_by_role_id.assert_awaited_once_with(
        7
    )
    role_service.log_context.put.assert_called_once_with("role", {"id": 7, "name": "原角色"})
    await assert_invalidation_after_commit(role_service, 1)


@pytest.mark.parametrize("ids", [[], [7, 8]])
async def test_role_batch_preserves_individual_delete_semantics(role_service, ids):
    """批删逐条校验、清理和记录日志，外层不再额外登记 ROLE 失效。"""
    role_service.security_settings.bizlog_enabled = True
    assert await unwrap(RoleServiceImpl.delete_role_batch)(role_service, ids) == len(ids)
    expected_calls = [call(role_id) for role_id in ids]
    assert role_service.validate_role_for_update.await_args_list == expected_calls
    assert role_service.role_mapper.delete_by_id.await_args_list == expected_calls
    assert (
        role_service.permission_service.role_menu_mapper.delete_list_by_role_id.await_args_list
        == expected_calls
    )
    assert (
        role_service.permission_service.user_role_mapper.delete_list_by_role_id.await_args_list
        == expected_calls
    )
    assert role_service.log_context.put.call_args_list == [
        call("role", {"id": role_id, "name": "原角色"}) for role_id in ids
    ]
    await assert_invalidation_after_commit(role_service, len(ids))


async def test_rejected_role_delete_does_not_mutate_or_invalidate(role_service):
    """角色校验失败时保留业务错误，不删除关系或登记缓存失效。"""
    error = ServiceException(ErrorCodeConstants.ROLE_NOT_EXISTS)
    role_service.validate_role_for_update.side_effect = error
    with pytest.raises(ServiceException) as raised:
        await role_service.delete_role(7)
    assert raised.value is error
    role_service.role_mapper.delete_by_id.assert_not_awaited()
    role_service.permission_service.role_menu_mapper.delete_list_by_role_id.assert_not_awaited()
    await assert_invalidation_after_commit(role_service, 0)


@pytest.fixture
def cold_cache(monkeypatch):
    """执行真实缓存装饰器的回源与发布判定，不连接 Redis。"""
    handler = SimpleNamespace(
        build_full_key=Mock(return_value="test:permission"),
        capture_generation=AsyncMock(return_value="generation"),
        publish_loaded_value=AsyncMock(),
    )

    async def get_or_load(**kwargs):
        """模拟未命中，让实际装饰器决定是否发布返回值。"""
        return await kwargs["load_and_publish"]()

    components = {
        CacheHandler: handler,
        CacheLoadThroughCoordinator: SimpleNamespace(get_or_load=get_or_load),
    }
    monkeypatch.setattr(
        ApplicationContext, "lookup", classmethod(lambda cls, kind: components[kind])
    )
    return handler


@pytest.mark.parametrize("menu_ids", [[], [7, 8]])
async def test_single_permission_caches_empty_and_nonempty_lists(cold_cache, menu_ids):
    """空菜单列表与非空列表均写缓存，且编号次序保持不变。"""
    service = MenuServiceImpl()
    service.menu_mapper = SimpleNamespace(
        select_list_by_permission=AsyncMock(
            return_value=[MenuDO(id=identifier) for identifier in menu_ids]
        )
    )
    result = await service.get_menu_id_list_by_permission_from_cache("system:test")
    assert result == menu_ids
    cold_cache.publish_loaded_value.assert_awaited_once_with(
        SystemCacheKeyConstants.PERMISSION_MENU_ID_LIST,
        "permission:system:test",
        result,
        "generation",
        3600,
    )


@pytest.mark.parametrize(
    ("permissions", "menus", "expected"),
    [
        (set(), [], {}),
        ({"system:test"}, [], {}),
        (
            {"system:test"},
            [MenuDO(id=7, permission="system:test"), MenuDO(id=8, permission="system:test")],
            {"system:test": [7, 8]},
        ),
    ],
)
async def test_batch_permissions_cache_empty_and_grouped_results(
    cold_cache, permissions, menus, expected
):
    """空输入、空查询和分组结果均缓存，空输入不访问 Mapper。"""
    service = MenuServiceImpl()
    service.menu_mapper = SimpleNamespace(select_list_by_permissions=AsyncMock(return_value=menus))
    assert await service.get_menu_ids_by_permissions(permissions) == expected
    cold_cache.publish_loaded_value.assert_awaited_once()
    published = cold_cache.publish_loaded_value.await_args.args
    assert published[0] == SystemCacheKeyConstants.PERMISSION_MENU_ID_LIST
    assert published[2:] == (expected, "generation", 3600)
    if permissions:
        service.menu_mapper.select_list_by_permissions.assert_awaited_once_with(permissions)
    else:
        service.menu_mapper.select_list_by_permissions.assert_not_awaited()
