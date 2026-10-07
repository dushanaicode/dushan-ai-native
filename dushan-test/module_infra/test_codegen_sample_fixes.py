import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from framework.common.exception import ServiceException
from framework.starter_di.context.application_context import ApplicationContext
from module_infra.controller.admin.codegen.codegen_controller import (
    CodegenController,
    codegen_controller,
)
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.service.codegen.codegen_service_impl import CodegenServiceImpl
from module_infra.util.codegen.codegen_builder_utils import CodegenBuilderUtils

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "name,class_name,module_name,business_name",
    [
        ("system_user", "User", "system", "user"),
        ("infra_codegen_table", "CodegenTable", "infra", "table"),
        ("record", "Record", "record", "record"),
        ("", "", "", ""),
        ("_record", "Record", "", "record"),
        ("record_", "", "record", ""),
        ("infra__record", "Record", "infra", "record"),
    ],
)
def test_codegen_names_preserve_separator_semantics(name, class_name, module_name, business_name):
    """表名首尾分隔符和空串仍遵循原来的命名合同。"""
    assert CodegenBuilderUtils.build_class_name(name) == class_name
    assert CodegenBuilderUtils.build_module_name(name) == module_name
    assert CodegenBuilderUtils.build_business_name(name) == business_name


@pytest.mark.parametrize(
    "ids,expected_remaining,expected_deleted",
    [
        ([], {1, 2, 3}, []),
        ([99], {1, 2, 3}, []),
        ([1, 99], {2, 3}, [1]),
        ([1, 1, 2, 99], {3}, [1, 2]),
        ([1, 2, 3], set(), [1, 2, 3]),
    ],
)
async def test_codegen_batch_delete_counts_only_hits(ids, expected_remaining, expected_deleted):
    """批删只统计命中行，重复和不存在编号不会重复删除关联列。"""
    remaining = {1, 2, 3}

    async def delete(identifier):
        """模拟 Mapper 按未删除记录返回受影响行数。"""
        if identifier not in remaining:
            return 0
        remaining.remove(identifier)
        return 1

    service = CodegenServiceImpl()
    service.codegen_table_mapper = SimpleNamespace(delete_by_id=AsyncMock(side_effect=delete))
    service.codegen_column_mapper = SimpleNamespace(delete_by_table_id=AsyncMock())
    count = await CodegenServiceImpl.delete_codegen_table_list.__wrapped__(service, ids)
    assert count == len(expected_deleted)
    assert remaining == expected_remaining
    assert service.codegen_column_mapper.delete_by_table_id.await_args_list == [
        call(identifier) for identifier in expected_deleted
    ]


@pytest.mark.parametrize("fail_cascade", [False, True])
async def test_codegen_batch_uses_one_transaction_and_propagates_cascade_failure(
    monkeypatch, fail_cascade
):
    """表和列的删除共用一个事务，列删除失败交给该事务回滚。"""
    transaction = AsyncMock()
    transaction.__aexit__.return_value = False
    database = SimpleNamespace(transaction=Mock(return_value=transaction))
    monkeypatch.setattr(ApplicationContext, "lookup", Mock(return_value=database))
    failure = RuntimeError("列删除失败")
    service = CodegenServiceImpl()
    service.codegen_table_mapper = SimpleNamespace(delete_by_id=AsyncMock(return_value=1))
    service.codegen_column_mapper = SimpleNamespace(
        delete_by_table_id=AsyncMock(side_effect=failure if fail_cascade else None)
    )
    if fail_cascade:
        with pytest.raises(RuntimeError) as caught:
            await service.delete_codegen_table_list([1])
        assert caught.value is failure
    else:
        assert await service.delete_codegen_table_list([1]) == 1
    database.transaction.assert_called_once_with(source=None, propagation="required")
    transaction.__aenter__.assert_awaited_once()
    transaction.__aexit__.assert_awaited_once()
    error_type, error, _ = transaction.__aexit__.await_args.args
    assert error_type is (RuntimeError if fail_cascade else None)
    assert error is (failure if fail_cascade else None)


async def test_codegen_single_delete_keeps_not_found_error():
    """单删仍校验表存在，缺失时不执行任何删除。"""
    service = CodegenServiceImpl()
    service.codegen_table_mapper = SimpleNamespace(
        select_by_id=AsyncMock(return_value=None), delete_by_id=AsyncMock()
    )
    service.codegen_column_mapper = SimpleNamespace(delete_by_table_id=AsyncMock())
    with pytest.raises(ServiceException) as caught:
        await CodegenServiceImpl.delete_codegen_table.__wrapped__(service, 99)
    assert caught.value.error_code == ErrorCodeConstants.CODEGEN_TABLE_NOT_EXISTS
    service.codegen_table_mapper.delete_by_id.assert_not_awaited()
    service.codegen_column_mapper.delete_by_table_id.assert_not_awaited()


@pytest.mark.parametrize("count", [0, 1, 2])
async def test_codegen_controller_returns_integer_count(count):
    """批删响应及其公开模型保留真实整数数量，包括零命中。"""
    service = SimpleNamespace(delete_codegen_table_list=AsyncMock(return_value=count))
    app = FastAPI()
    app.include_router(codegen_controller)
    dependency = (
        inspect.signature(CodegenController.delete_codegen_table_list)
        .parameters["codegen_service"]
        .default.dependency
    )
    app.dependency_overrides[dependency] = lambda: service
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete("/codegen/delete-list", params=[("ids", "1"), ("ids", "2")])
    assert response.status_code == 200
    result = response.json()
    assert result["code"] == 0
    assert type(result["data"]) is int
    assert result["data"] == count
    service.delete_codegen_table_list.assert_awaited_once_with([1, 2])
