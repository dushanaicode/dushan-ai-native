from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from framework.common.enums import StatusEnum
from framework.common.exception import ServiceException
from module_system.api.user.admin_user_api_impl import AdminUserApiImpl
from module_system.dal.dataobject.dept.post_do import PostDO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.dept.post_service_impl import PostServiceImpl
from module_system.service.user.admin_user_service_impl import AdminUserServiceImpl

pytestmark = pytest.mark.unit


async def test_subordinates_without_led_departments_do_not_query_users():
    """未负责任何部门时返回空列表，不扩大用户查询范围。"""
    service = AdminUserServiceImpl()
    service.dept_service = SimpleNamespace(
        get_dept_list_by_leader_user_id=AsyncMock(return_value=[]),
        get_child_dept_list_by_ids=AsyncMock(),
    )
    service.user_mapper = SimpleNamespace(select_list_by_dept_ids=AsyncMock())
    api = AdminUserApiImpl()
    api.user_service = service

    assert await api.get_user_list_by_subordinate(10) == []

    service.dept_service.get_dept_list_by_leader_user_id.assert_awaited_once_with(10)
    service.dept_service.get_child_dept_list_by_ids.assert_not_awaited()
    service.user_mapper.select_list_by_dept_ids.assert_not_awaited()


@pytest.mark.parametrize("child_ids", [[], [100, 200, 300, 300]])
async def test_subordinates_include_led_and_child_departments_excluding_self(child_ids):
    """下属查询合并负责人部门和子部门，保留顺序并排除本人。"""
    service = AdminUserServiceImpl()
    service.dept_service = SimpleNamespace(
        get_dept_list_by_leader_user_id=AsyncMock(
            return_value=[SimpleNamespace(id=100), SimpleNamespace(id=200)]
        ),
        get_child_dept_list_by_ids=AsyncMock(
            return_value=[SimpleNamespace(id=id) for id in child_ids]
        ),
    )
    users = [
        AdminUserDO(id=id, username=f"user{id}", nickname=f"用户{id}", status=1)
        for id in (10, 11, 12)
    ]
    service.user_mapper = SimpleNamespace(select_list_by_dept_ids=AsyncMock(return_value=users))
    api = AdminUserApiImpl()
    api.user_service = service

    result = await api.get_user_list_by_subordinate(10)

    assert [(user.id, user.nickname) for user in result] == [(11, "用户11"), (12, "用户12")]
    service.user_mapper.select_list_by_dept_ids.assert_awaited_once_with({100, 200, *child_ids})
    service.dept_service.get_child_dept_list_by_ids.assert_awaited_once()


@pytest.mark.parametrize("ids", [[], [11, 12]])
async def test_user_map_uses_service_list_and_empty_ids_do_not_query_database(ids):
    """用户索引沿列表链路转换，空集合由服务阻止查库。"""
    service = AdminUserServiceImpl()
    service.user_mapper = SimpleNamespace(
        select_batch_ids=AsyncMock(
            return_value=[
                AdminUserDO(id=id, username=f"user{id}", nickname=f"用户{id}", status=1)
                for id in ids
            ]
        )
    )
    api = AdminUserApiImpl()
    api.user_service = service

    result = await api.get_user_map(ids)

    assert list(result) == ids
    assert all(key == user.id for key, user in result.items())
    if ids:
        service.user_mapper.select_batch_ids.assert_awaited_once_with(ids)
    else:
        service.user_mapper.select_batch_ids.assert_not_awaited()


@pytest.mark.parametrize("ids", [None, [], [101]])
async def test_user_post_validation_delegates_submitted_ids(ids):
    """未提交岗位不校验，已提交集合交由岗位服务统一判断。"""
    service = AdminUserServiceImpl()
    service.post_service = SimpleNamespace(validate_post_list=AsyncMock())

    await service._validate_post_list(ids)

    if ids is None:
        service.post_service.validate_post_list.assert_not_awaited()
    else:
        service.post_service.validate_post_list.assert_awaited_once_with(ids)


@pytest.mark.parametrize(
    "posts,error",
    [
        ([], ErrorCodeConstants.POST_NOT_FOUND),
        (
            [PostDO(id=101, name="禁用岗位", status=StatusEnum.DISABLE.code)],
            ErrorCodeConstants.POST_NOT_ENABLE,
        ),
        ([PostDO(id=101, name="启用岗位", status=StatusEnum.ENABLE.code)], None),
    ],
)
async def test_user_post_validation_preserves_missing_and_disabled_errors(posts, error):
    """复用真实岗位服务后仍拒绝缺失和禁用岗位。"""
    posts_service = PostServiceImpl()
    posts_service.post_mapper = SimpleNamespace(select_batch_ids=AsyncMock(return_value=posts))
    service = AdminUserServiceImpl()
    service.post_service = posts_service

    if error is None:
        await service._validate_post_list([101])
    else:
        with pytest.raises(ServiceException) as caught:
            await service._validate_post_list([101])
        assert caught.value.error_code == error

    posts_service.post_mapper.select_batch_ids.assert_awaited_once_with([101])
