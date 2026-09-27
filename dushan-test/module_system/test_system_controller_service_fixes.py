import json
from inspect import unwrap
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from module_system.controller.admin.oauth2.vo.client.oauth2_client_save_req_vo import (
    OAuth2ClientSaveReqVO,
)
from module_system.convert.auth.auth_convert import AuthConvert
from module_system.dal.dataobject.permission.menu_do import MenuDO
from module_system.dal.mapper.dept.dept_user_post_mapper import DeptUserPostMapper
from module_system.framework.notification.channel.mail_notification_handler import (
    MailNotificationHandler,
)
from module_system.service.permission.menu_service_impl import MenuServiceImpl
from module_system.service.permission.permission_cache_service_impl import (
    PermissionCacheServiceImpl,
)
from module_system.service.user.admin_user_service_impl import AdminUserServiceImpl


async def create(client, path, body):
    result = (await client.post(f"/admin-api/system/{path}/create", json=body)).json()
    assert result["code"] == 0, result
    return result["data"]


def oauth_body():
    return {
        "clientId": "regression" + uuid4().hex,
        "secret": "Regression-OAuth-Secret-123456789!",
        "name": "Regression client",
        "logo": "https://example.test/logo.png",
        "status": 1,
        "userType": 2,
        "accessTokenValiditySeconds": 3600,
        "refreshTokenValiditySeconds": 7200,
        "redirectUris": ["https://example.test/callback"],
        "authorizedGrantTypes": ["authorization_code", "refresh_token"],
    }


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize("mode", ["omitted", "empty", "null", "replace", "invalid"])
async def test_user_post_update_preserves_explicit_field_semantics(
    mode, admin_client, system_database
):
    suffix = uuid4().hex[:10]
    posts = [
        await create(
            admin_client,
            "dept/post",
            {"name": suffix + str(i), "code": suffix + str(i), "sort": i, "status": 1},
        )
        for i in range(3)
    ]
    body = {
        "username": "usr" + suffix,
        "nickname": "Before",
        "password": "Test123!",
        "postIds": posts[:2],
    }
    identifier = await create(admin_client, "user", body)
    change = {"id": identifier, "username": body["username"], "nickname": "After"}
    if mode != "omitted":
        change["postIds"] = {
            "empty": [],
            "null": None,
            "replace": posts[1:],
            "invalid": ["9223372036854775807"],
        }[mode]
    result = (await admin_client.put("/admin-api/system/user/update", json=change)).json()
    assert result["code"] == (1002005000 if mode == "invalid" else 0), result
    expected = (
        posts[:2] if mode in {"omitted", "invalid"} else posts[1:] if mode == "replace" else []
    )
    with system_database[2].cursor() as cursor:
        cursor.execute("SELECT nickname, post_ids FROM system_users WHERE id=%s", (identifier,))
        nickname, value = cursor.fetchone()
        assert nickname == ("Before" if mode == "invalid" else "After")
        assert json.loads(value) == (None if mode == "null" else [int(p) for p in expected])
        cursor.execute(
            "SELECT post_id FROM system_user_post WHERE user_id=%s AND deleted=0", (identifier,)
        )
        assert {str(row[0]) for row in cursor.fetchall()} == set(expected)


@pytest.mark.asyncio(loop_scope="module")
async def test_user_department_omission_and_denied_reassignment(
    admin_client, system_database, monkeypatch
):
    departments = [
        await create(
            admin_client,
            "dept",
            {"name": "dept" + uuid4().hex[:8], "parentId": "0", "sort": i, "status": 1},
        )
        for i in range(2)
    ]
    body = {
        "username": "dept" + uuid4().hex[:8],
        "nickname": "Before",
        "password": "Test123!",
        "deptId": departments[0],
    }
    identifier = await create(admin_client, "user", body)
    original = PermissionCacheServiceImpl.invalidate_user_caches
    calls = []

    async def invalidate(self):
        calls.append(True)
        await original(self)

    monkeypatch.setattr(PermissionCacheServiceImpl, "invalidate_user_caches", invalidate)
    change = {"id": identifier, "username": body["username"], "nickname": "After"}
    assert (await admin_client.put("/admin-api/system/user/update", json=change)).json()[
        "code"
    ] == 0
    assert calls == []
    change["deptId"] = departments[1]
    # 部门是现有数据归属不可变列，保留框架拒绝及事务回滚契约。
    assert (await admin_client.put("/admin-api/system/user/update", json=change)).json()[
        "code"
    ] == 1005008
    assert calls == []
    with system_database[2].cursor() as cursor:
        cursor.execute("SELECT dept_id FROM system_users WHERE id=%s", (identifier,))
        assert str(cursor.fetchone()[0]) == departments[0]


@pytest.mark.asyncio
async def test_user_cache_comparison_keeps_snapshot_when_mapper_mutates_entity():
    from module_system.controller.admin.user.vo.user.user_save_req_vo import UserSaveReqVO
    from module_system.dal.dataobject.user.admin_user_do import AdminUserDO

    user = AdminUserDO(id=10, username="fixture", nickname="Before", dept_id=20)
    service = AdminUserServiceImpl()
    service.access_policy = SimpleNamespace(protect_owner_account=lambda *args: None)
    service.tenant = SimpleNamespace(get_required_tenant_id=lambda: "1")
    service.revisions = SimpleNamespace(advance=AsyncMock())
    service.security_settings = SimpleNamespace(bizlog_enabled=False)
    service._validate_user_for_create_or_update = AsyncMock(return_value=user)
    service.permission_cache = SimpleNamespace(invalidate_user_caches=AsyncMock())

    async def update(request):
        user.dept_id = request.dept_id
        return user

    service.user_mapper = SimpleNamespace(update_by_id=update)
    request = UserSaveReqVO(id="10", username="fixture", nickname="After", dept_id="30")
    await unwrap(AdminUserServiceImpl.update_user)(service, request)
    service.permission_cache.invalidate_user_caches.assert_awaited_once()


@pytest.mark.asyncio(loop_scope="module")
async def test_user_post_write_failure_rolls_back_main_row(
    admin_client, system_database, monkeypatch
):
    suffix = uuid4().hex[:10]
    post = await create(
        admin_client, "dept/post", {"name": suffix, "code": suffix, "sort": 1, "status": 1}
    )
    body = {
        "username": "rollback" + suffix,
        "nickname": "Before",
        "password": "Test123!",
        "postIds": [],
    }
    identifier = await create(admin_client, "user", body)

    async def fail(self, user_id, post_ids):
        assert str(user_id) == identifier
        raise RuntimeError("fixture association write failure")

    monkeypatch.setattr(DeptUserPostMapper, "insert_batch_by_user_id", fail)
    changed = {
        "id": identifier,
        "username": body["username"],
        "nickname": "After",
        "postIds": [post],
    }
    result = (await admin_client.put("/admin-api/system/user/update", json=changed)).json()
    assert result["code"] == 500, result
    with system_database[2].cursor() as cursor:
        cursor.execute("SELECT nickname,post_ids FROM system_users WHERE id=%s", (identifier,))
        nickname, posts = cursor.fetchone()
        assert nickname == "Before" and json.loads(posts) == []
        cursor.execute(
            "SELECT COUNT(*) FROM system_user_post WHERE user_id=%s AND deleted=0", (identifier,)
        )
        assert cursor.fetchone()[0] == 0


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize("scopes", ["omitted", None, [], ["profile"]])
async def test_oauth_scopes_save_and_real_authorize(scopes, admin_client, system_database):
    body = oauth_body()
    if scopes != "omitted":
        body["scopes"] = scopes
    result = (await admin_client.post("/admin-api/system/oauth2/client/create", json=body)).json()
    if scopes is None:
        assert result["code"] == 422, result
        assert any(field["field"] == "scopes" for field in result["error"]["fields"])
        return
    assert result["code"] == 0, result
    identifier = result["data"]
    authorized = (
        await admin_client.get(
            "/admin-api/system/oauth2/open/authorize", params={"client_id": body["clientId"]}
        )
    ).json()
    assert authorized["code"] == 0, authorized
    assert [scope["key"] for scope in authorized["data"]["scopes"]] == (
        [] if scopes == "omitted" else scopes
    )
    body.update(id=identifier, scopes=["profile"])
    assert (await admin_client.put("/admin-api/system/oauth2/client/update", json=body)).json()[
        "code"
    ] == 0
    body.pop("scopes")
    assert (await admin_client.put("/admin-api/system/oauth2/client/update", json=body)).json()[
        "code"
    ] == 0
    with system_database[2].cursor() as cursor:
        cursor.execute("SELECT scopes FROM system_oauth2_client WHERE id=%s", (identifier,))
        assert json.loads(cursor.fetchone()[0]) == []
    invalid = (
        await admin_client.put(
            "/admin-api/system/oauth2/client/update", json={**body, "scopes": None}
        )
    ).json()
    assert invalid["code"] == 422, invalid


@pytest.mark.parametrize("field", ["accessTokenValiditySeconds", "refreshTokenValiditySeconds"])
@pytest.mark.parametrize("value", [0, -1])
def test_oauth_non_positive_ttl_rejected_at_field(field, value):
    with pytest.raises(ValidationError) as caught:
        OAuth2ClientSaveReqVO.model_validate({**oauth_body(), field: value})
    assert caught.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize("field", ["accessTokenValiditySeconds", "refreshTokenValiditySeconds"])
def test_oauth_ttl_respects_integer_storage_boundary(field):
    for value in (1, 2147483647):
        OAuth2ClientSaveReqVO.model_validate({**oauth_body(), field: value})
    with pytest.raises(ValidationError) as caught:
        OAuth2ClientSaveReqVO.model_validate({**oauth_body(), field: 2147483648})
    assert caught.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize(
    "field", ["clientId", "name", "logo", "description", "additionalInformation"]
)
def test_oauth_varchar_length_boundary(field):
    prefix = "https://example.test/" if field == "logo" else ""
    valid = prefix + "a" * (255 - len(prefix))
    OAuth2ClientSaveReqVO.model_validate({**oauth_body(), field: valid})
    with pytest.raises(ValidationError) as caught:
        OAuth2ClientSaveReqVO.model_validate({**oauth_body(), field: valid + "a"})
    assert caught.value.errors()[0]["loc"] == (field,)


@pytest.mark.asyncio
async def test_menu_sort_nested_ties_and_existing_filters():
    def menu(identifier, parent=0, sort=0, kind="page", **overrides):
        return MenuDO(
            id=identifier,
            parent_id=parent,
            sort=sort,
            name=str(identifier),
            kind=kind,
            status=1,
            visible=True,
            keep_alive=True,
            always_show=True,
            data_permission=False,
            **overrides,
        )

    rows = [
        menu(10, sort=20),
        menu(20, sort=10, kind="group"),
        menu(30, parent=20, sort=20),
        menu(40, parent=20, sort=10),
        menu(41, parent=20, sort=10),
        menu(50, kind="group"),
        menu(60, kind="action"),
    ]
    hidden = menu(70, sort=0)
    hidden.visible = False
    disabled = menu(80, kind="group")
    disabled.status = 0
    rows.extend([hidden, disabled, menu(90, parent=80)])
    rows = await MenuServiceImpl().filter_disable_menus(rows)
    tree = AuthConvert._build_menu_tree(list(reversed(rows)))
    assert [node.id for node in tree] == ["70", "20", "10"]
    assert tree[0].visible is False
    assert [node.id for node in tree[1].children] == ["40", "41", "30"]
    assert AuthConvert._build_menu_tree([]) == []


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize("mode", ["empty", "invalid", "unsupported", "user", "department"])
async def test_notice_recipient_resolution_has_explicit_result(mode, admin_client, system_database):
    department = await create(
        admin_client,
        "dept",
        {"name": "notice" + uuid4().hex[:8], "parentId": "0", "sort": 1, "status": 1},
    )
    user = await create(
        admin_client,
        "user",
        {
            "username": "notice" + uuid4().hex[:8],
            "nickname": "Receiver",
            "password": "Test123!",
            "deptId": department,
        },
    )
    notice = await create(
        admin_client,
        "notification",
        {
            "title": "Recipient regression",
            "content": "Test",
            "type": 2,
            "userType": 1 if mode == "unsupported" else 2,
            "channels": ["INTERNAL"],
            "status": 1,
            "publisher": "Fixture",
        },
    )
    body = {"id": notice}
    if mode == "invalid":
        body["userIds"] = ["9223372036854775807"]
    elif mode in {"user", "unsupported"}:
        body["userIds"] = [user]
    elif mode == "department":
        body["deptIds"] = [department]
    result = (
        await admin_client.post("/admin-api/system/notification/push-targets", json=body)
    ).json()
    expected = 0 if mode in {"user", "department"} else 400 if mode == "unsupported" else 1002028002
    assert result["code"] == expected, result
    with system_database[2].cursor() as cursor:
        cursor.execute(
            "SELECT total_count, success_count, fail_count FROM system_notification_notice_log WHERE notice_id=%s",
            (notice,),
        )
        assert cursor.fetchall() == (((1, 1, 0),) if expected == 0 else ())


@pytest.mark.asyncio(loop_scope="module")
async def test_notice_partial_channel_failure_keeps_messages_and_reports_failure(
    admin_client, system_database, monkeypatch
):
    user = await create(
        admin_client,
        "user",
        {"username": "channel" + uuid4().hex[:8], "nickname": "Receiver", "password": "Test123!"},
    )
    notice = await create(
        admin_client,
        "notification",
        {
            "title": "Channel failure",
            "content": "Test",
            "type": 2,
            "userType": 2,
            "channels": ["MAIL", "INTERNAL"],
            "status": 1,
            "publisher": "Fixture",
        },
    )

    async def fail(*args, **kwargs):
        raise OSError("fixture mail channel unavailable")

    monkeypatch.setattr(MailNotificationHandler, "send", fail)
    result = (
        await admin_client.post(
            "/admin-api/system/notification/push-targets", json={"id": notice, "userIds": [user]}
        )
    ).json()
    assert result["code"] == 503, result
    with system_database[2].cursor() as cursor:
        cursor.execute(
            "SELECT total_count, success_count, fail_count FROM system_notification_notice_log WHERE notice_id=%s",
            (notice,),
        )
        assert cursor.fetchall() == ((1, 0, 1),)
        cursor.execute(
            "SELECT COUNT(*) FROM system_notification_message WHERE notice_id=%s AND user_id=%s AND deleted=0",
            (notice, user),
        )
        assert cursor.fetchone()[0] == 1


def test_representative_id_examples_match_input_and_output_contracts():
    from module_infra.controller.admin.file.vo.file.file_create_req_vo import FileCreateReqVO
    from module_system.controller.admin.auth.vo.auth_permission_info_resp_vo import (
        AuthPermissionInfoRespVO,
    )
    from module_system.controller.admin.permission.vo.menu.menu_save_vo import MenuSaveVO
    from module_system.controller.admin.user.vo.user.user_resp_vo import UserRespVO
    from module_system.controller.admin.user.vo.user.user_save_req_vo import UserSaveReqVO

    for model in (
        UserSaveReqVO,
        OAuth2ClientSaveReqVO,
        FileCreateReqVO,
        AuthPermissionInfoRespVO,
        UserRespVO,
    ):
        example = model.model_json_schema()["examples"][0]
        model.model_validate(example)
    example = UserSaveReqVO.model_json_schema()["examples"][0]
    assert isinstance(example["id"], str) and all(
        isinstance(value, str) for value in example["postIds"]
    )
    assert type(example["sex"]) is int
    menu = MenuSaveVO.model_json_schema()["examples"][0]
    assert MenuSaveVO.model_validate({**menu, "parentId": "0"}).parent_id == 0
    response = AuthPermissionInfoRespVO.model_validate(
        AuthPermissionInfoRespVO.model_json_schema()["examples"][0]
    ).model_dump(by_alias=True)
    assert response["menus"][0]["parentId"] == "0"


def test_oauth_scopes_seed_uses_non_null_arrays(system_database):
    with system_database[2].cursor() as cursor:
        cursor.execute("SELECT scopes FROM system_oauth2_client")
        scopes = cursor.fetchall()
        assert scopes
        assert all(isinstance(json.loads(row[0]), list) for row in scopes)
        cursor.execute(
            "SELECT IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='system_oauth2_client' AND COLUMN_NAME='scopes'"
        )
        assert cursor.fetchone()[0] == "NO"
