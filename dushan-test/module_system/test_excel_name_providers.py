from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.dialects import mysql

from framework.starter_database.ddl.ddl_cli import DdlCli
from module_system.dal.dataobject.dept.dept_do import DeptDO
from module_system.dal.dataobject.dept.post_do import PostDO
from module_system.dal.mapper.dept.dept_mapper import DeptMapper
from module_system.dal.mapper.dept.post_mapper import PostMapper
from module_system.service.dept.dept_service_impl import DeptServiceImpl
from module_system.service.dept.post_service_impl import PostServiceImpl
from module_system.spi.dept.dept_info_provider_adapter import DeptInfoProviderAdapter
from module_system.spi.dept.post_info_provider_adapter import PostInfoProviderAdapter

DdlCli._import_models("module_system")
DdlCli._import_models("module_infra")

pytestmark = pytest.mark.unit

PROVIDERS = [
    (DeptInfoProviderAdapter, DeptServiceImpl, DeptMapper, DeptDO, "dept_mapper"),
    (PostInfoProviderAdapter, PostServiceImpl, PostMapper, PostDO, "post_mapper"),
]


@pytest.fixture(params=PROVIDERS, ids=["department", "post"])
def provider_chain(request):
    """运行真实 Provider、Service 与 Mapper，仅截获受管读取边界。"""
    adapter_type, service_type, mapper_type, model_type, mapper_name = request.param
    mapper = mapper_type()
    result = Mock()
    result.scalars.return_value.all.return_value = []
    mapper.read = AsyncMock(return_value=result)
    delegate = service_type()
    setattr(delegate, mapper_name, mapper)
    provider = adapter_type()
    provider.delegate = delegate
    return provider, mapper, result, model_type


@pytest.mark.parametrize("names", [[], ["不存在"], ["运维", "运维", "不存在", "研发%_"]])
async def test_provider_resolves_names_in_one_exact_query(provider_chain, names):
    """批量查询精确名称，不退化为逐名读取，也不增加状态限制。"""
    provider, mapper, result, model_type = provider_chain
    rows = (
        [model_type(id=1, name="运维", status=0), model_type(id=2, name="研发%_", status=1)]
        if len(names) > 1
        else []
    )
    result.scalars.return_value.all.return_value = rows

    assert await provider.ids(names) == {row.name: row.id for row in rows}

    mapper.read.assert_awaited_once()
    (statement,) = mapper.read.await_args.args
    conditions = list(statement._where_criteria)
    assert len(conditions) == 1
    assert conditions[0].left.name == "name"
    assert conditions[0].right.value == names
    assert " IN " in str(statement.compile(dialect=mysql.dialect()))


async def test_provider_rejects_duplicate_names_including_disabled_entries(provider_chain):
    """同名部门或岗位不得因状态不同而静默选择最后一条。"""
    provider, mapper, result, model_type = provider_chain
    result.scalars.return_value.all.return_value = [
        model_type(id=1, name="重名", status=1),
        model_type(id=2, name="重名", status=0),
    ]

    with pytest.raises(ValueError, match="名称重复，不能唯一确定部门或岗位"):
        await provider.ids(["重名"])

    mapper.read.assert_awaited_once()


@pytest.mark.parametrize("ids", [[], [999], [1, 2, 1, 999]])
async def test_provider_names_preserves_empty_missing_duplicate_and_disabled_ids(
    provider_chain, ids
):
    """名称投影只按给定 ID 查询，空集合不会意外读取全表。"""
    provider, mapper, result, model_type = provider_chain
    rows = (
        [model_type(id=1, name="运维", status=0), model_type(id=2, name="同名", status=1)]
        if len(ids) > 1
        else []
    )
    result.scalars.return_value.all.return_value = rows

    assert await provider.names(ids) == {row.id: row.name for row in rows}

    if ids:
        mapper.read.assert_awaited_once()
        (statement,) = mapper.read.await_args.args
        conditions = list(statement._where_criteria)
        assert len(conditions) == 1
        assert conditions[0].left.name == "id"
        assert conditions[0].right.value == ids
    else:
        mapper.read.assert_not_awaited()


@pytest.mark.parametrize("method,values", [("ids", ["运维"]), ("names", [1])])
async def test_provider_propagates_query_failures(provider_chain, method, values):
    """查询失败不被替换为空字典，避免导入或导出静默丢失名称。"""
    provider, mapper, _, _ = provider_chain
    mapper.read.side_effect = RuntimeError("query failed")

    with pytest.raises(RuntimeError, match="query failed"):
        await getattr(provider, method)(values)
