from datetime import datetime
from functools import partial
from inspect import unwrap
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from framework.common.exception import GlobalErrorCodeConstants, IllegalArgumentException
from framework.starter_database.ddl.ddl_cli import DdlCli
from module_system.controller.admin.oauth2.oauth2_user_controller import Oauth2UserController
from module_system.controller.admin.oauth2.vo.user.oauth2_user_update_req_vo import (
    OAuth2UserUpdateReqVO,
)
from module_system.controller.admin.user.user_profile_controller import UserProfileController
from module_system.controller.admin.user.vo.profile.user_profile_update_req_vo import (
    UserProfileUpdateReqVO,
)
from module_system.dal.dataobject.dept.post_do import PostDO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.dal.dataobject.user.admin_user_profile_do import AdminUserProfileDO
from module_system.service.user.admin_user_service_impl import AdminUserServiceImpl
from module_system.service.user.user_profile_service_impl import UserProfileServiceImpl

DdlCli._import_models("module_system")
DdlCli._import_models("module_infra")

pytestmark = pytest.mark.unit


@pytest.fixture
def user_service():
    """提供真实用户服务与无外部资源的鉴权、校验和写入依赖。"""
    service = AdminUserServiceImpl()
    service.access_policy = SimpleNamespace(protect_owner_account=Mock())
    service.tenant = SimpleNamespace(get_required_tenant_id=Mock(return_value="1"))
    service.revisions = SimpleNamespace(advance=AsyncMock())
    service._validate_user_exists = AsyncMock()
    service._validate_email_unique = AsyncMock()
    service._validate_mobile_unique = AsyncMock()
    service.user_mapper = SimpleNamespace(update_by_id=AsyncMock())
    return service


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"bio": None, "tags": []},
        {"nickname": "新昵称"},
        {"email": None, "mobile": None, "sex": None, "avatar": None},
        {"sex": 0, "avatar": "https://example.com/avatar.png"},
    ],
)
async def test_basic_profile_updates_only_supplied_basic_fields(user_service, values):
    """基本资料保留显式空值、零值与省略字段，并将头像 URL 写为字符串。"""
    req = UserProfileUpdateReqVO(**values)

    await unwrap(AdminUserServiceImpl.update_user_profile)(user_service, 1024, req)

    expected = {
        name: value
        for name, value in values.items()
        if name in {"nickname", "email", "mobile", "sex", "avatar"}
    }
    if expected:
        entity = user_service.user_mapper.update_by_id.await_args.args[0]
        assert {
            key: value for key, value in vars(entity).items() if key != "_sa_instance_state"
        } == {
            "id": 1024,
            **expected,
        }
    else:
        user_service.user_mapper.update_by_id.assert_not_awaited()
    user_service.access_policy.protect_owner_account.assert_called_once_with(1024, "1")
    user_service.revisions.advance.assert_awaited_once()
    user_service._validate_user_exists.assert_awaited_once_with(1024)
    user_service._validate_email_unique.assert_awaited_once_with(1024, req.email)
    user_service._validate_mobile_unique.assert_awaited_once_with(1024, req.mobile)


async def test_basic_profile_rejects_null_nickname_before_writing(user_service):
    """昵称响应要求字符串，拒绝将显式 null 写入并破坏后续读取。"""
    with pytest.raises(IllegalArgumentException) as failure:
        await unwrap(AdminUserServiceImpl.update_user_profile)(
            user_service, 1024, UserProfileUpdateReqVO(nickname=None, email=None)
        )

    assert failure.value.error_code == GlobalErrorCodeConstants.BAD_REQUEST
    assert failure.value.msg == "用户昵称不能为空"
    user_service.user_mapper.update_by_id.assert_not_awaited()


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize(
    "values",
    [
        {},
        {"nickname": "新昵称", "email": None},
        {"bio": None},
        {
            "bio": None,
            "tags": None,
            "address": None,
            "skills": None,
            "work_scope": None,
            "expertise": None,
            "communication_style": None,
            "ai_preference": None,
        },
        {"tags": [], "skills": [], "ai_preference": {}, "bio": ""},
        {"bio": "简介", "work_scope": "研发", "communication_style": "technical"},
    ],
)
async def test_extended_profile_preserves_supplied_fields_for_insert_and_update(existing, values):
    """详情新增与更新只写白名单内的已提交字段，清空不会误清其他详情。"""
    service = UserProfileServiceImpl()
    service.get_user_profile = AsyncMock(
        return_value=AdminUserProfileDO(id=4096, user_id=1024) if existing else None
    )
    service.admin_user_profile_mapper = SimpleNamespace(
        insert=AsyncMock(), update_by_id=AsyncMock()
    )

    await unwrap(UserProfileServiceImpl.create_or_update_profile)(
        service, 1024, UserProfileUpdateReqVO(**values)
    )

    expected = {name: value for name, value in values.items() if name not in {"nickname", "email"}}
    if not expected:
        service.get_user_profile.assert_not_awaited()
        service.admin_user_profile_mapper.insert.assert_not_awaited()
        service.admin_user_profile_mapper.update_by_id.assert_not_awaited()
        return
    write = (
        service.admin_user_profile_mapper.update_by_id
        if existing
        else service.admin_user_profile_mapper.insert
    )
    entity = write.await_args.args[0]
    assert {key: value for key, value in vars(entity).items() if key != "_sa_instance_state"} == {
        "user_id": 1024,
        **({"id": 4096} if existing else {}),
        **expected,
    }
    assert all(AdminUserProfileDO.__table__.c[name].nullable for name in expected)


@pytest.mark.parametrize(
    "values",
    [
        {"nickname": "OAuth 昵称"},
        {"nickname": "OAuth 昵称", "email": None, "mobile": None, "sex": None},
        {"nickname": "OAuth 昵称", "mobile": "13800138000", "sex": 0},
    ],
)
async def test_oauth_profile_conversion_preserves_supplied_fields(user_service, values):
    """OAuth2 转换后调用真实用户服务，省略字段不写入而显式 null 可清空。"""
    service = SimpleNamespace(
        update_user_profile=AsyncMock(
            wraps=partial(unwrap(AdminUserServiceImpl.update_user_profile), user_service)
        )
    )
    security = SimpleNamespace(require=Mock(return_value=SimpleNamespace(account_id="1024")))

    result = await unwrap(Oauth2UserController.update_user_info)(
        OAuth2UserUpdateReqVO(**values), service, security
    )

    assert result.data is True
    converted = service.update_user_profile.await_args.args[1]
    assert converted.model_fields_set == set(values)
    entity = user_service.user_mapper.update_by_id.await_args.args[0]
    assert {key: value for key, value in vars(entity).items() if key != "_sa_instance_state"} == {
        "id": 1024,
        **values,
    }
    assert all(AdminUserDO.__table__.c[name].nullable for name in values)


@pytest.mark.parametrize("post_ids", [None, [], [2048]])
async def test_profile_controller_passes_posts_as_a_list(post_ids):
    """无岗位不查询服务且返回空数组，有岗位继续转换真实岗位列表。"""
    now = datetime(2026, 10, 6, 12, 0)
    user = AdminUserDO(
        id=1024,
        username="fixture",
        nickname="测试用户",
        dept_id=None,
        post_ids=post_ids,
        login_ip="127.0.0.1",
        login_date=now,
        create_time=now,
    )
    posts = SimpleNamespace(get_post_list=AsyncMock(return_value=[PostDO(id=2048, name="研发")]))
    security = SimpleNamespace(require=Mock(return_value=SimpleNamespace(account_id="1024")))

    result = await unwrap(UserProfileController.get_user_profile)(
        user_service=SimpleNamespace(get_user=AsyncMock(return_value=user)),
        dept_service=SimpleNamespace(get_dept=AsyncMock()),
        post_service=posts,
        permission_service=SimpleNamespace(
            get_user_role_id_list_by_user_id=AsyncMock(return_value=[])
        ),
        role_service=SimpleNamespace(get_role_list_by_ids=AsyncMock(return_value=[])),
        profile_service=SimpleNamespace(get_user_profile=AsyncMock(return_value=None)),
        security=security,
    )

    assert result.data.to_response()["posts"] == (
        [{"id": "2048", "name": "研发"}] if post_ids else []
    )
    if post_ids:
        posts.get_post_list.assert_awaited_once_with(post_ids)
    else:
        posts.get_post_list.assert_not_awaited()
