from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call

import pytest
from sqlalchemy.dialects import mysql

from framework.common.exception import ServiceException
from framework.starter_database.ddl.ddl_cli import DdlCli
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_security.public import SecurityErrorCodes, SecurityException
from module_system.dal.dataobject.permission.role_menu_do import RoleMenuDO
from module_system.dal.mapper.permission.role_menu_mapper import RoleMenuMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.enums.permission.role_code_enum import RoleCodeEnum
from module_system.service.permission.permission_service_impl import PermissionServiceImpl
from module_system.service.tenant.tenant_service_impl import TenantServiceImpl

DdlCli._import_models("module_system")
DdlCli._import_models("module_infra")

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("current", "wanted"),
    [(set(), set()), ({1, 2}, {1, 2}), (set(), {1, 2}), ({1, 2}, set()), ({1, 2}, {2, 3, 4})],
)
async def test_mapper_sync_preserves_intersection_and_writes_only_differences(current, wanted):
    """保留共有关系，只软删撤销项并批量添加新项。"""
    mapper = RoleMenuMapper()
    mapper.soft_delete_by_condition = AsyncMock()
    mapper.insert_batch = AsyncMock()

    assert await mapper.sync_menu_ids(17, current, wanted) is (current != wanted)

    mapper.insert_batch.assert_awaited_once()
    (inserted,) = mapper.insert_batch.await_args.args
    assert all(isinstance(row, RoleMenuDO) for row in inserted)
    assert {(row.role_id, row.menu_id) for row in inserted} == {
        (17, menu_id) for menu_id in wanted - current
    }
    if current - wanted:
        mapper.soft_delete_by_condition.assert_awaited_once()
        role_condition, menu_condition = mapper.soft_delete_by_condition.await_args.args
        assert role_condition.left.name == "role_id"
        assert list(role_condition.compile(dialect=mysql.dialect()).params.values()) == [17]
        assert menu_condition.left.name == "menu_id"
        assert set(menu_condition.right.value) == current - wanted
    else:
        mapper.soft_delete_by_condition.assert_not_awaited()


@pytest.fixture
def permission_sync(monkeypatch):
    """执行真实事务装饰器、Service 和差量 Mapper，仅替换持久化与身份资源。"""
    events = []

    @asynccontextmanager
    async def transaction(**kwargs):
        """记录事务边界，验证失败不会被服务吞掉。"""
        events.append("begin")
        try:
            yield
        except BaseException:
            events.append("rollback")
            raise
        else:
            events.append("commit")

    database = SimpleNamespace(transaction=transaction)
    monkeypatch.setattr(ApplicationContext, "lookup", Mock(return_value=database))
    service = PermissionServiceImpl()
    service.roles = SimpleNamespace(
        select_by_id=AsyncMock(return_value=SimpleNamespace(id=17, code="operator"))
    )
    service.menus = SimpleNamespace(select_by_ids=AsyncMock(return_value=[object(), object()]))
    service.security = SimpleNamespace(
        require=Mock(return_value=SimpleNamespace(account_id="42", tenant_id="8"))
    )
    service.access_policy = SimpleNamespace(
        menu_ids=AsyncMock(return_value={1, 2, 3}), require_owner=Mock()
    )
    mapper = RoleMenuMapper()
    mapper.select_list_by_role_id = AsyncMock(
        return_value=[SimpleNamespace(menu_id=1), SimpleNamespace(menu_id=2)]
    )
    mapper.soft_delete_by_condition = AsyncMock(side_effect=lambda *args: events.append("delete"))
    mapper.insert_batch = AsyncMock(side_effect=lambda *args: events.append("insert"))
    service.role_menu_mapper = mapper
    service.revisions = SimpleNamespace(
        advance=AsyncMock(side_effect=lambda: events.append("version"))
    )
    service.events = SimpleNamespace(
        invalidate_all=AsyncMock(side_effect=lambda: events.append("cache"))
    )
    return service, events


@pytest.mark.parametrize("wanted", [{2, 3}, {1, 2}])
async def test_permission_sync_keeps_transaction_revision_and_cache_even_when_unchanged(
    permission_sync, wanted
):
    """关系变化和重复提交均保留原有版本推进与缓存失效语义。"""
    service, events = permission_sync
    await service.assign_role_menu(17, wanted)
    service.access_policy.menu_ids.assert_awaited_once_with("42", "8")
    service.role_menu_mapper.select_list_by_role_id.assert_awaited_once_with(17)
    service.revisions.advance.assert_awaited_once()
    service.events.invalidate_all.assert_awaited_once()
    assert events == (
        ["begin", "delete", "insert", "version", "cache", "commit"]
        if wanted == {2, 3}
        else ["begin", "insert", "version", "cache", "commit"]
    )


@pytest.mark.parametrize("failure", ["role", "owner", "menu", "package"])
async def test_permission_rejects_invalid_grants_before_relationship_writes(
    permission_sync, failure
):
    """角色存在性、平台身份、菜单存在性和套餐边界均先于落库。"""
    service, events = permission_sync
    expected = ServiceException
    if failure == "role":
        service.roles.select_by_id.return_value = None
        code = ErrorCodeConstants.ROLE_NOT_EXISTS.code
    elif failure == "owner":
        service.roles.select_by_id.return_value.code = RoleCodeEnum.SUPER_ADMIN.code
        service.access_policy.require_owner.side_effect = SecurityException(
            SecurityErrorCodes.DENIED
        )
        expected = SecurityException
        code = SecurityErrorCodes.DENIED.code
    elif failure == "menu":
        service.menus.select_by_ids.return_value = [object()]
        code = ErrorCodeConstants.MENU_NOT_EXISTS.code
    else:
        service.access_policy.menu_ids.return_value = {1, 2}
        expected = SecurityException
        code = SecurityErrorCodes.DENIED.code

    with pytest.raises(expected) as caught:
        await service.assign_role_menu(17, {2, 3})

    assert caught.value.error_code.code == code
    service.role_menu_mapper.select_list_by_role_id.assert_not_awaited()
    service.role_menu_mapper.soft_delete_by_condition.assert_not_awaited()
    service.role_menu_mapper.insert_batch.assert_not_awaited()
    service.revisions.advance.assert_not_awaited()
    service.events.invalidate_all.assert_not_awaited()
    assert events == ["begin", "rollback"]


async def test_permission_sync_write_failure_rolls_back_without_version_or_cache(permission_sync):
    """批量新增失败向外传播，让原事务回滚已经执行的撤销操作。"""
    service, events = permission_sync
    service.role_menu_mapper.insert_batch.side_effect = RuntimeError("insert failed")

    with pytest.raises(RuntimeError, match="insert failed"):
        await service.assign_role_menu(17, {2, 3})

    assert events == ["begin", "delete", "rollback"]
    service.revisions.advance.assert_not_awaited()
    service.events.invalidate_all.assert_not_awaited()


@pytest.mark.parametrize("wanted", [{2, 3}, {1, 2}, set()])
async def test_tenant_sync_preserves_admin_full_set_and_regular_intersection(wanted):
    """管理员跟随套餐全集，普通角色只缩减，并继续同步后续角色。"""
    service = TenantServiceImpl()
    service.roles = SimpleNamespace(
        select_list=AsyncMock(
            return_value=[
                SimpleNamespace(id=17, code=RoleCodeEnum.TENANT_ADMIN.code),
                SimpleNamespace(id=18, code="operator"),
                SimpleNamespace(id=19, code="reader"),
            ]
        )
    )
    current_by_role = {17: {1, 2}, 18: {1, 2}, 19: {2}}
    service.role_menus = SimpleNamespace(
        select_list_by_role_id=AsyncMock(
            side_effect=lambda role_id: [
                SimpleNamespace(menu_id=menu_id) for menu_id in current_by_role[role_id]
            ]
        ),
        sync_menu_ids=AsyncMock(side_effect=lambda role_id, current, desired: current != desired),
    )

    changed = await service._apply_role_menus(wanted)

    assert changed is (wanted != {1, 2})
    assert service.role_menus.sync_menu_ids.await_args_list == [
        call(17, {1, 2}, wanted),
        call(18, {1, 2}, {1, 2} & wanted),
        call(19, {2}, {2} & wanted),
    ]


@pytest.mark.parametrize("changed", [False, True])
async def test_tenant_revision_advances_only_when_relationships_change(changed):
    """租户同步保持工作负载和事务边界，仅关系变化时推进版本。"""
    service = TenantServiceImpl()
    events = []

    @asynccontextmanager
    async def scope(*args):
        """记录工作负载与事务上下文的进入和退出。"""
        events.append(("enter", args))
        yield
        events.append(("exit", args))

    service.workloads = SimpleNamespace(scope=scope)
    service.database = SimpleNamespace(transaction=scope)
    service._apply_role_menus = AsyncMock(return_value=changed)
    service.revisions = SimpleNamespace(advance=AsyncMock())

    await service.update_tenant_role_menu(8, {2, 3})

    service._apply_role_menus.assert_awaited_once_with({2, 3})
    assert service.revisions.advance.await_count == int(changed)
    assert events == [
        ("enter", ("system.tenant.provision", "8")),
        ("enter", ()),
        ("exit", ()),
        ("exit", ("system.tenant.provision", "8")),
    ]
