import inspect
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr
from starlette.requests import HTTPConnection

from framework.common.enums import ApplicationEnvironmentEnum, UserTypeEnum
from framework.common.exception import GlobalErrorCodeConstants, ServiceException
from framework.starter_web.public import RequestContext
from module_system.api.social.dto.social_user_bind_req_dto import SocialUserBindReqDTO
from module_system.controller.admin.auth.auth_controller import AuthController
from module_system.controller.admin.auth.vo.auth.auth_login_req_vo import AuthLoginReqVO
from module_system.controller.admin.auth.vo.auth.auth_recovery_send_req_vo import (
    AuthRecoverySendReqVO,
)
from module_system.controller.admin.auth.vo.auth.auth_reset_password_req_vo import (
    AuthResetPasswordReqVO,
)
from module_system.controller.admin.auth.vo.auth.auth_sms_send_req_vo import AuthSmsSendReqVO
from module_system.controller.admin.auth.vo.auth.auth_social_login_req_vo import (
    AuthSocialLoginReqVO,
)
from module_system.dal.dataobject.social.social_user_do import SocialUserDO
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.enums.sms.sms_scene_enum import SmsSceneEnum
from module_system.service.auth.auth_admin_auth_service_impl import AuthAdminAuthServiceImpl
from module_system.service.auth.bo.email_reset_state_bo import EmailResetStateBO
from module_system.service.permission.permission_service_impl import PermissionServiceImpl
from module_system.service.sms.sms_code_service_impl import SmsCodeServiceImpl
from module_system.service.social.social_user_service_impl import SocialUserServiceImpl
from module_system.service.user.admin_user_service_impl import AdminUserServiceImpl

pytestmark = pytest.mark.unit
READONLY_ROLES = [{"readonly"}, {"readonly", "common"}, {"readonly", "super_admin"}]
WRITABLE_ROLES = [set(), {"common"}, {"tenant_admin"}, {"super_admin"}]


@pytest.fixture
def auth_state(monkeypatch):
    """仅替换存储/厂商边界，认证、绑定、角色判定和改密执行真实方法。"""

    def create(roles):
        user = SimpleNamespace(
            id=10100000010004,
            username="demo",
            status=1,
            email="demo@example.com",
            mobile="13800000000",
            password="original-hash",
            credential_revision=7,
        )
        permission = PermissionServiceImpl()
        permission.roles = SimpleNamespace(
            read_from_primary=AsyncMock(
                return_value=SimpleNamespace(
                    scalars=lambda: SimpleNamespace(
                        all=lambda: [SimpleNamespace(code=role) for role in roles]
                    )
                )
            )
        )
        permission.access_policy = SimpleNamespace(is_owner=lambda *args: "super_admin" in roles)
        permission.tenant = SimpleNamespace(get_required_tenant_id=lambda: "1")
        bindings = ["existing-identity"]

        async def delete_existing(*args):
            bindings.clear()

        async def insert_binding(value):
            bindings.append(value.social_user_id)

        social = SocialUserServiceImpl()
        social.permission_service = permission
        social._auth_social_user = AsyncMock(
            return_value=SimpleNamespace(id=456, type=10, openid="new-identity")
        )
        social.social_user_mapper = SimpleNamespace(
            select_by_type_and_openid=AsyncMock(return_value=SimpleNamespace(id=456))
        )
        social.social_user_bind_mapper = SimpleNamespace(
            select_by_user_type_and_social_user_id=AsyncMock(return_value=None),
            delete_by_user_type_and_social_user_id=AsyncMock(),
            delete_by_user_type_and_user_id_and_social_type=AsyncMock(side_effect=delete_existing),
            insert=AsyncMock(side_effect=insert_binding),
        )
        social.bind_social_user = inspect.unwrap(SocialUserServiceImpl.bind_social_user).__get__(
            social
        )
        social.unbind_social_user = inspect.unwrap(
            SocialUserServiceImpl.unbind_social_user
        ).__get__(social)

        async def update_password(values, condition):
            user.password = values["password"]
            user.credential_revision += 1

        users = AdminUserServiceImpl()
        users._validate_user_exists = AsyncMock(return_value=user)
        users.password_encoder = SimpleNamespace(hash=AsyncMock(return_value="changed-hash"))
        users.user_mapper = SimpleNamespace(
            update_by_condition=AsyncMock(side_effect=update_password)
        )
        users.change_password = inspect.unwrap(AdminUserServiceImpl.change_password).__get__(users)
        auth = AuthAdminAuthServiceImpl()
        auth.permission_service = permission
        auth.social_user_service = social
        auth.user_service = users
        auth.tenant = permission.tenant
        auth.authenticate = AsyncMock(return_value=user)
        auth._validate_captcha = AsyncMock()
        auth._create_token_after_login_success = AsyncMock(return_value="session")
        auth.sms_code_service = SimpleNamespace(use_sms_code=AsyncMock())
        auth.authentication = SimpleNamespace(
            user_by_mobile=AsyncMock(return_value=user),
            user_by_email=AsyncMock(return_value=user),
            user_by_id=AsyncMock(return_value=user),
        )
        auth._reset_sms_password = inspect.unwrap(
            AuthAdminAuthServiceImpl._reset_sms_password
        ).__get__(auth)
        auth.settings = SimpleNamespace(message_signing_key=SecretStr("test-message-key" * 3))
        auth.reset_settings = SimpleNamespace(max_attempts=5)
        identifier = auth._email_identifier(user.email)
        now = datetime.now(timezone.utc).timestamp()
        state = EmailResetStateBO(
            code_digest=auth._email_code_digest(identifier, "123456"),
            user_id=user.id,
            credential_revision=user.credential_revision,
            issued_at=now,
            expires_at=now + 600,
            attempts=0,
            daily_count=1,
        )
        auth.cache = SimpleNamespace(
            get=AsyncMock(
                return_value=SimpleNamespace(hit=True, value=state.model_dump(by_alias=False))
            ),
            set=AsyncMock(),
        )

        @asynccontextmanager
        async def lock(identifier):
            yield

        @asynccontextmanager
        async def transaction():
            yield SimpleNamespace(
                scalars=AsyncMock(return_value=SimpleNamespace(one_or_none=lambda: user))
            )

        auth._email_reset_lock = lock
        auth.database = SimpleNamespace(transaction=transaction)
        monkeypatch.setattr(
            RequestContext,
            "current",
            lambda: RequestContext(
                HTTPConnection({"type": "http", "headers": []}), "trace-1", "127.0.0.1"
            ),
        )
        return SimpleNamespace(
            auth=auth,
            social=social,
            permission=permission,
            users=users,
            user=user,
            bindings=bindings,
        )

    return create


def login_request():
    return AuthLoginReqVO(
        username="demo",
        password="123456",
        social_type=10,
        social_code="visitor-oauth-code",
        social_state="valid-state",
    )


@pytest.mark.parametrize("roles", READONLY_ROLES)
async def test_password_login_cannot_replace_readonly_social_identity(auth_state, roles):
    state = auth_state(roles)
    with pytest.raises(ServiceException) as error:
        await state.auth.login(login_request())
    assert error.value.error_code == GlobalErrorCodeConstants.DEMO_DENY
    assert state.bindings == ["existing-identity"]
    state.social._auth_social_user.assert_not_awaited()
    state.social.social_user_bind_mapper.insert.assert_not_awaited()
    state.auth._create_token_after_login_success.assert_not_awaited()


@pytest.mark.parametrize("roles", READONLY_ROLES)
@pytest.mark.parametrize("operation", ["bind", "unbind"])
async def test_social_identity_mutation_rejects_readonly_target(auth_state, roles, operation):
    state = auth_state(roles)
    with pytest.raises(ServiceException) as error:
        if operation == "bind":
            await state.social.bind_social_user(
                SocialUserBindReqDTO(
                    user_id=state.user.id,
                    user_type=UserTypeEnum.ADMIN.code,
                    type=10,
                    code="visitor-oauth-code",
                    state="valid-state",
                )
            )
        else:
            await state.social.unbind_social_user(
                state.user.id, UserTypeEnum.ADMIN.code, 10, "existing-identity"
            )
    assert error.value.error_code.code == 901
    assert state.bindings == ["existing-identity"]
    state.social._auth_social_user.assert_not_awaited()
    state.social.social_user_bind_mapper.delete_by_user_type_and_social_user_id.assert_not_awaited()


@pytest.mark.parametrize("roles", READONLY_ROLES)
@pytest.mark.parametrize("channel", ["sms", "email"])
async def test_anonymous_password_reset_preserves_readonly_credentials(auth_state, roles, channel):
    state = auth_state(roles)
    with pytest.raises(ServiceException) as error:
        await state.auth.reset_password(
            AuthResetPasswordReqVO(
                channel=channel,
                mobile=state.user.mobile if channel == "sms" else None,
                email=state.user.email if channel == "email" else None,
                code="123456",
                password="Changed123",
            )
        )
    assert error.value.error_code.code == 901
    assert state.user.password == "original-hash"
    assert state.user.credential_revision == 7
    state.users.password_encoder.hash.assert_not_awaited()
    state.users.user_mapper.update_by_condition.assert_not_awaited()


@pytest.mark.parametrize("roles", WRITABLE_ROLES)
async def test_regular_accounts_can_login_bind_and_unbind(auth_state, roles):
    state = auth_state(roles)
    assert await state.auth.login(login_request()) == "session"
    assert state.bindings == [456]
    await state.social.unbind_social_user(
        state.user.id, UserTypeEnum.ADMIN.code, 10, "new-identity"
    )
    assert state.bindings == []


@pytest.mark.parametrize("roles", WRITABLE_ROLES)
@pytest.mark.parametrize("channel", ["sms", "email"])
async def test_regular_accounts_can_reset_password(auth_state, roles, channel):
    state = auth_state(roles)
    await state.auth.reset_password(
        AuthResetPasswordReqVO(
            channel=channel,
            mobile=state.user.mobile if channel == "sms" else None,
            email=state.user.email if channel == "email" else None,
            code="123456",
            password="Changed123",
        )
    )
    assert state.user.password == "changed-hash"
    assert state.user.credential_revision == 8
    state.users.password_encoder.hash.assert_awaited_once_with("Changed123")


@pytest.mark.parametrize("roles", READONLY_ROLES)
async def test_readonly_password_login_keeps_session_access(auth_state, roles):
    state = auth_state(roles)
    assert await state.auth.login(AuthLoginReqVO(username="demo", password="123456")) == "session"
    state.social._auth_social_user.assert_not_awaited()


@pytest.fixture
def recovery_state(auth_state, monkeypatch):
    """真实验证码生成、限流和消费使用内存存储，不连接数据库或 Redis。"""
    clock = SimpleNamespace(now=datetime(2026, 1, 15, 12, tzinfo=timezone.utc))
    dates = SimpleNamespace(now=lambda: clock.now, to_timezone=lambda value: value)
    module_clock = SimpleNamespace(
        now=lambda tz=None: clock.now, fromtimestamp=datetime.fromtimestamp
    )
    monkeypatch.setattr(
        "module_system.service.auth.auth_admin_auth_service_impl.datetime", module_clock
    )
    monkeypatch.setattr("module_system.service.sms.sms_code_service_impl.datetime", module_clock)
    monkeypatch.setattr(
        "module_system.service.auth.auth_admin_auth_service_impl.secrets.randbelow",
        lambda maximum: 123,
    )

    def create(roles, *, missing=False):
        state = auth_state(roles)
        if missing:
            state.auth.authentication.user_by_mobile.return_value = None
            state.auth.authentication.user_by_email.return_value = None
        state.clock = clock
        state.records = []
        state.cached = {}

        async def cache_get(key, identifier):
            return SimpleNamespace(
                hit=identifier in state.cached, value=state.cached.get(identifier)
            )

        async def cache_set(key, identifier, value, **kwargs):
            state.cached[identifier] = value

        async def insert(record):
            record.id = len(state.records) + 1
            record.create_time = clock.now.replace(tzinfo=None)
            state.records.append(record)

        async def update(values, *conditions):
            for name, value in values.items():
                setattr(state.records[-1], name, value)
            return 1

        @asynccontextmanager
        async def lock(*args, **kwargs):
            yield

        state.auth.cache = SimpleNamespace(
            get=AsyncMock(side_effect=cache_get),
            set=AsyncMock(side_effect=cache_set),
            eval_atomic=AsyncMock(return_value=1),
        )
        state.auth.captcha_service = SimpleNamespace(verification=AsyncMock(return_value=True))
        state.auth.mail_sender = SimpleNamespace(send_single_mail=AsyncMock())
        state.auth.date_utils = dates
        state.auth.reset_settings = SimpleNamespace(
            resend_seconds=60,
            max_daily=2,
            expire_seconds=600,
            max_attempts=5,
            mail_template_code="reset",
        )
        sms = SmsCodeServiceImpl()
        sms.tenant = state.auth.tenant
        sms.environment = ApplicationEnvironmentEnum.PRODUCTION
        sms.settings = SimpleNamespace(
            begin_code=1000,
            end_code=9999,
            send_frequency=60,
            send_maximum_quantity_per_day=2,
            expire_times=600,
            max_attempts=5,
        )
        sms.dates = dates
        sms.database = SimpleNamespace(transaction=lock)
        sms.locks = SimpleNamespace(with_lock=lock)
        sms.cache = state.auth.cache
        sms.mapper = SimpleNamespace(
            select_last_by_mobile=AsyncMock(
                side_effect=lambda *args: state.records[-1] if state.records else None
            ),
            insert=AsyncMock(side_effect=insert),
            update_by_condition=AsyncMock(side_effect=update),
        )
        sms.sender = SimpleNamespace(send_single_sms=AsyncMock())
        sms.use_sms_code = inspect.unwrap(SmsCodeServiceImpl.use_sms_code).__get__(sms)
        state.auth.sms_code_service = sms
        return state

    return create


@pytest.mark.parametrize("roles", READONLY_ROLES)
@pytest.mark.parametrize("channel", ["send-sms-code", "sms", "email"])
async def test_readonly_recovery_matches_missing_response_and_limits(
    recovery_state, roles, channel
):
    missing = recovery_state(set(), missing=True)
    readonly = recovery_state(roles)
    states = [missing, readonly]

    async def send(state):
        if channel == "send-sms-code":
            return await inspect.unwrap(AuthController.send_sms_code)(
                None,
                AuthSmsSendReqVO(
                    mobile=state.user.mobile, scene=SmsSceneEnum.ADMIN_MEMBER_RESET_PASSWORD.code
                ),
                state.auth,
            )
        return await inspect.unwrap(AuthController.send_recovery_code)(
            None,
            AuthRecoverySendReqVO(
                channel=channel,
                mobile=state.user.mobile if channel == "sms" else None,
                email=state.user.email if channel == "email" else None,
            ),
            state.auth,
        )

    for count in (1, 2):
        responses = [await send(state) for state in states]
        assert responses[0].model_dump() == responses[1].model_dump()
        assert responses[0].code == 0 and responses[0].data == (6 if channel == "email" else 4)
        for state in states:
            state.auth.mail_sender.send_single_mail.assert_not_awaited()
            state.auth.sms_code_service.sender.send_single_sms.assert_not_awaited()
            if channel == "email":
                cached = state.cached[state.auth._email_identifier(state.user.email)]
                assert cached["daily_count"] == count
                assert cached["user_id"] is None and cached["credential_revision"] is None
            else:
                assert state.records[-1].today_index == count
        limited = []
        for state in states:
            with pytest.raises(ServiceException) as error:
                await send(state)
            limited.append(error.value.error_code)
        assert (
            limited
            == [
                ErrorCodeConstants.AUTH_RESET_SEND_LIMIT
                if channel == "email"
                else ErrorCodeConstants.SMS_CODE_SEND_TOO_FAST
            ]
            * 2
        )
        missing.clock.now += timedelta(seconds=61)

    for state in states:
        with pytest.raises(ServiceException) as error:
            await send(state)
        assert error.value.error_code == (
            ErrorCodeConstants.AUTH_RESET_SEND_LIMIT
            if channel == "email"
            else ErrorCodeConstants.SMS_CODE_EXCEED_SEND_MAXIMUM_QUANTITY_PER_DAY
        )
        with pytest.raises(ServiceException) as reset_error:
            await state.auth.reset_password(
                AuthResetPasswordReqVO(
                    channel="email" if channel == "email" else "sms",
                    email=state.user.email if channel == "email" else None,
                    mobile=state.user.mobile if channel != "email" else None,
                    code="000123" if channel == "email" else state.records[-1].code,
                    password="Changed123",
                )
            )
        expected = (
            GlobalErrorCodeConstants.DEMO_DENY
            if state is readonly and channel != "email"
            else ErrorCodeConstants.AUTH_RESET_CODE_INVALID
        )
        assert reset_error.value.error_code == expected
        assert state.user.password == "original-hash" and state.user.credential_revision == 7
        state.users.password_encoder.hash.assert_not_awaited()
        state.users.user_mapper.update_by_condition.assert_not_awaited()


@pytest.mark.parametrize("roles", WRITABLE_ROLES)
@pytest.mark.parametrize("channel", ["legacy-sms", "sms", "email"])
async def test_regular_accounts_can_request_recovery_codes(auth_state, roles, channel):
    state = auth_state(roles)
    state.auth.captcha_service = SimpleNamespace(verification=AsyncMock(return_value=True))
    state.auth.sms_code_service.send_sms_code = AsyncMock(return_value=6)
    state.auth.mail_sender = SimpleNamespace(send_single_mail=AsyncMock())
    state.auth.cache.get.return_value = SimpleNamespace(hit=False)
    state.auth.reset_settings = SimpleNamespace(expire_seconds=600, mail_template_code="reset")
    if channel == "legacy-sms":
        result = await state.auth.send_sms_code(
            AuthSmsSendReqVO(
                mobile=state.user.mobile, scene=SmsSceneEnum.ADMIN_MEMBER_RESET_PASSWORD.code
            )
        )
    else:
        result = await state.auth.send_recovery_code(
            AuthRecoverySendReqVO(
                channel=channel,
                mobile=state.user.mobile if channel == "sms" else None,
                email=state.user.email if channel == "email" else None,
            )
        )
    assert result == 6
    if channel == "email":
        state.auth.mail_sender.send_single_mail.assert_awaited_once()
    else:
        state.auth.sms_code_service.send_sms_code.assert_awaited_once()


@pytest.mark.parametrize("roles", READONLY_ROLES + WRITABLE_ROLES)
async def test_social_login_preserves_readonly_identity_profile(auth_state, roles):
    state = auth_state(roles)
    existing = SocialUserDO(
        id=456,
        type=10,
        openid="provider-identity",
        client_id="client",
        subject_type="user",
        application_id="app",
        nickname="original",
        avatar="original-avatar",
        token="original-token",
        code="old-code",
        state="old-state",
    )
    identity = SimpleNamespace(
        subject=existing.openid,
        client_id=existing.client_id,
        subject_type=existing.subject_type,
        application_id=existing.application_id,
        nickname="changed",
        username="new-name",
        avatar="new-avatar",
        raw={"name": "changed"},
    )
    state.social.social_client_service = SimpleNamespace(
        get_auth_user=AsyncMock(
            return_value=SimpleNamespace(
                identity=identity,
                tokens=SimpleNamespace(
                    access_token=SecretStr("new-token"), to_storage_json=lambda: SecretStr("{}")
                ),
            )
        )
    )
    state.social.social_user_mapper = SimpleNamespace(
        read=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: existing)),
        update_by_id=AsyncMock(),
        select_by_id=AsyncMock(return_value=existing),
        insert=AsyncMock(),
    )
    state.social.social_user_bind_mapper.select_by_user_type_and_social_user_id.return_value = (
        SimpleNamespace(user_id=state.user.id)
    )
    state.social._auth_social_user = inspect.unwrap(
        SocialUserServiceImpl._auth_social_user
    ).__get__(state.social)
    assert (
        await state.auth.social_login(
            AuthSocialLoginReqVO(type=10, code="new-code", state="new-state")
        )
        == "session"
    )
    if "readonly" in roles:
        state.social.social_user_mapper.update_by_id.assert_not_awaited()
        assert existing.nickname == "original" and existing.token == "original-token"
    else:
        state.social.social_user_mapper.update_by_id.assert_awaited_once()
        assert state.social.social_user_mapper.update_by_id.await_args.args[0].nickname == "changed"
    state.social.social_user_bind_mapper.delete_by_user_type_and_user_id_and_social_type.assert_not_awaited()
