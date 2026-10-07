from inspect import unwrap
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from framework.common.enums import StatusEnum
from framework.common.exception import ServiceException
from module_system.dal.dataobject.dept.post_do import PostDO
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.dept.post_service_impl import PostServiceImpl

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("ids", [[10, 20], [20, 10, 20], []])
async def test_delete_post_batch_loads_once_and_preserves_delete_arguments(ids):
    """批删只加载一次，保持禁用岗位、重复 ID 和空集合的删除语义。"""
    posts = [
        PostDO(id=20, status=StatusEnum.DISABLE.code),
        PostDO(id=10, status=StatusEnum.ENABLE.code),
    ]
    expected_count = len(set(ids))
    service = PostServiceImpl()
    service.post_mapper = SimpleNamespace(
        select_batch_ids=AsyncMock(return_value=posts if ids else []),
        select_by_id=AsyncMock(),
        delete_by_ids=AsyncMock(return_value=expected_count),
    )

    result = await unwrap(PostServiceImpl.delete_post_batch)(service, ids)

    assert result == expected_count
    service.post_mapper.select_batch_ids.assert_awaited_once_with(ids)
    service.post_mapper.select_by_id.assert_not_awaited()
    service.post_mapper.delete_by_ids.assert_awaited_once_with(ids)


@pytest.mark.parametrize("ids", [[30, 10, 20], [10, 30, 20], [10, 20, 30], [30]])
async def test_delete_post_batch_rejects_missing_ids_before_any_delete(ids):
    """任何位置存在不可见或缺失岗位时，整批失败且不执行删除。"""
    service = PostServiceImpl()
    service.post_mapper = SimpleNamespace(
        select_batch_ids=AsyncMock(return_value=[PostDO(id=10), PostDO(id=20)]),
        select_by_id=AsyncMock(),
        delete_by_ids=AsyncMock(),
    )

    with pytest.raises(ServiceException) as error:
        await unwrap(PostServiceImpl.delete_post_batch)(service, ids)

    assert error.value.error_code == ErrorCodeConstants.POST_NOT_FOUND
    service.post_mapper.select_batch_ids.assert_awaited_once_with(ids)
    service.post_mapper.select_by_id.assert_not_awaited()
    service.post_mapper.delete_by_ids.assert_not_awaited()
