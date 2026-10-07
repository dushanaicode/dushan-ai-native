from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from framework.common.enums import StatusEnum
from framework.starter_database.ddl.ddl_cli import DdlCli
from framework.starter_di.public import ApplicationContext
from module_infra.dal.cache.infra_cache_key_constants import InfraCacheKeyConstants
from module_infra.service.cache.cache_service_impl import CacheServiceImpl
from module_infra.service.file.file_config_service_impl import FileConfigServiceImpl

DdlCli._import_models("module_system")
DdlCli._import_models("module_infra")


@pytest.mark.parametrize("operation", ["update", "delete"])
@pytest.mark.parametrize("commit", [True, False])
async def test_file_client_eviction_runs_only_after_successful_commit(
    monkeypatch, operation, commit
):
    """更新和删除只在提交后释放真实客户端，回滚不影响已使用的客户端。"""
    service = FileConfigServiceImpl()
    service.factory = SimpleNamespace(evict=AsyncMock())
    callbacks = []

    @asynccontextmanager
    async def transaction(**kwargs):
        try:
            yield
            service.factory.evict.assert_not_awaited()
            if not commit:
                raise RuntimeError("提交失败")
            for callback, name in callbacks:
                assert name == f"file-config-{operation}"
                await callback()
        finally:
            callbacks.clear()

    database = SimpleNamespace(
        transaction=transaction,
        after_commit=lambda callback, *, name: callbacks.append((callback, name)),
    )
    monkeypatch.setattr(ApplicationContext, "lookup", lambda _: database)
    service.database = database
    service._require = AsyncMock(
        return_value=SimpleNamespace(id=7, storage=1, config={}, master=False)
    )
    service.files = SimpleNamespace(select_count_by_config_id=AsyncMock(return_value=0))
    service.mapper = SimpleNamespace(update_by_id=AsyncMock(), delete_by_id=AsyncMock())
    service._config = Mock(return_value={})
    request = SimpleNamespace(
        id=7,
        storage=1,
        config={},
        to_write_dict=lambda **kwargs: {"id": 7, "storage": 1, "name": "存储"},
    )

    async def write():
        if operation == "update":
            await service.update_file_config(request)
        else:
            await service.delete_file_config(7)

    if commit:
        await write()
        service.factory.evict.assert_awaited_once_with(7)
    else:
        with pytest.raises(RuntimeError, match="提交失败"):
            await write()
        service.factory.evict.assert_not_awaited()


async def test_master_switch_uses_current_database_selection_without_cache():
    """默认客户端每次按当前主配置查询，切换无需无消费者的 Redis 失效回调。"""
    service = FileConfigServiceImpl()
    rows = [
        SimpleNamespace(id=7, storage=1, config={}, status=StatusEnum.ENABLE.code),
        SimpleNamespace(id=8, storage=1, config={}, status=StatusEnum.ENABLE.code),
    ]
    service.mapper = SimpleNamespace(select_by_master=AsyncMock(side_effect=rows))
    service.factory = SimpleNamespace(
        get_or_create_client=AsyncMock(side_effect=["client-7", "client-8"])
    )
    assert await service.get_master_file_client() == "client-7"
    assert await service.get_master_file_client() == "client-8"
    assert [call.args[0] for call in service.factory.get_or_create_client.await_args_list] == [7, 8]


async def test_master_update_keeps_lock_and_database_writes_without_unused_cache_callback():
    """主配置切换保留锁和数据库更新，不登记闲置缓存的提交回调。"""
    service = FileConfigServiceImpl()
    service._require = AsyncMock(return_value=SimpleNamespace(status=StatusEnum.ENABLE.code))
    session = SimpleNamespace(execute=AsyncMock())

    @asynccontextmanager
    async def transaction():
        yield session

    service.database = SimpleNamespace(transaction=transaction, after_commit=Mock())
    service.mapper = SimpleNamespace(update_by_condition=AsyncMock(), update_by_id=AsyncMock())
    await service.update_file_config_master.__wrapped__(service, 8)
    assert session.execute.await_args.args[0]._for_update_arg is not None
    service.mapper.update_by_condition.assert_awaited_once()
    assert service.mapper.update_by_id.await_args.args[0].id == 8
    assert service.mapper.update_by_id.await_args.args[0].master is True
    service.database.after_commit.assert_not_called()


def test_unused_file_cache_is_absent_from_registry_and_cleanup_presets():
    """键注册与业务清理预设同步移除闲置缓存。"""
    assert "FILE_CONFIG_CACHE" not in vars(InfraCacheKeyConstants)
    assert "infra:file_config_cache" not in CacheServiceImpl.BUSINESS_KEYS
