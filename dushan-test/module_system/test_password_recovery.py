import asyncio
import hashlib
import re
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from framework.starter_cache.public import CacheHandler
from framework.starter_security.public import SecurityRealm, SecurityService
from framework.starter_web.public import RoutePolicy
from module_system.dal.cache.cache_key_constants import SystemCacheKeys
from module_system.dal.dataobject.mail.mail_account_do import MailAccountDO
from module_system.dal.dataobject.mail.mail_template_do import MailTemplateDO
from module_system.dal.dataobject.sms.sms_channel_do import SmsChannelDO
from module_system.dal.dataobject.sms.sms_template_do import SmsTemplateDO
from module_system.dal.mapper.mail.mail_account_mapper import MailAccountMapper
from module_system.dal.mapper.mail.mail_template_mapper import MailTemplateMapper
from module_system.dal.mapper.sms.sms_channel_mapper import SmsChannelMapper
from module_system.dal.mapper.sms.sms_template_mapper import SmsTemplateMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.mq.producer.mail.mail_producer import MailProducer
from module_system.mq.producer.sms.sms_producer import SmsProducer
from module_system.service.sms.sms_code_service_impl import SmsCodeServiceImpl
from module_system.service.workload.system_workload_service import SystemWorkloadService

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def recovery_templates(system_app, admin_client):
    application, database = system_app.state.application_context, system_app.state.database
    with application.execution(), database.scope():
        token = admin_client.headers["Authorization"].removeprefix("Bearer ")
        async with application.container.get(SecurityService).authorized(
            token, RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
        ):
            async with database.transaction():
                account = await application.container.get(MailAccountMapper).insert(
                    MailAccountDO(
                        mail="sender@example.com",
                        username="test",
                        password="test-only",
                        host="127.0.0.1",
                        port=2525,
                        ssl_enable=False,
                        starttls_enable=False,
                    )
                )
                mail = await application.container.get(MailTemplateMapper).insert(
                    MailTemplateDO(
                        name="Recovery",
                        code="admin-reset-password",
                        account_id=account.id,
                        nickname="Native",
                        title="Reset code",
                        content="Code {code}; expires in {minutes} minutes",
                        params=["code", "minutes"],
                        status=1,
                    )
                )
                channel = await application.container.get(SmsChannelMapper).insert(
                    SmsChannelDO(
                        signature="Test",
                        code="ALIYUN",
                        status=1,
                        api_key="test-only",
                        api_secret="test-only",
                    )
                )
                sms = await application.container.get(SmsTemplateMapper).insert(
                    SmsTemplateDO(
                        type=1,
                        status=1,
                        code="admin-reset-password",
                        name="Recovery",
                        content="Code {code}",
                        params=["code"],
                        api_template_id="approved-test",
                        channel_id=channel.id,
                        channel_code=channel.code,
                    )
                )
    return {"mail": mail.id, "sms": sms.id, "channel": channel.id}


async def create_user(admin_client):
    suffix = uuid4().hex[:10]
    user = {
        "username": "r" + suffix,
        "nickname": "Recovery",
        "password": "Original123",
        "email": suffix + "@example.com",
        "mobile": "139" + str(int(suffix, 16) % 100_000_000).zfill(8),
    }
    result = (await admin_client.post("/admin-api/system/user/create", json=user)).json()
    assert result["code"] == 0, result
    return {**user, "id": result["data"]}


async def request(system_app, path, data, *, tenant_id="1", ip="127.0.0.110"):
    async with AsyncClient(
        transport=ASGITransport(app=system_app, client=(ip, 10000)), base_url="http://testserver"
    ) as client:
        return (
            await client.post(
                "/admin-api/system/auth/" + path, json=data, headers={"X-Tenant-Id": tenant_id}
            )
        ).json()


async def cache_state(system_app, email, updates=None, tenant_id="1"):
    application, database = system_app.state.application_context, system_app.state.database
    with application.execution(), database.scope():
        async with application.container.get(SystemWorkloadService).scope("system.auth", tenant_id):
            cache = application.container.get(CacheHandler)
            identifier = hashlib.sha256(email.casefold().encode()).hexdigest()
            found = await cache.get(SystemCacheKeys.EMAIL_PASSWORD_RESET, identifier)
            if updates is not None:
                value = {**found.value, **updates}
                await cache.set(SystemCacheKeys.EMAIL_PASSWORD_RESET, identifier, value)
                return value
            return found


async def test_email_reset_templates_single_use_and_credential_revocation(
    system_app, system_database, admin_client, recovery_templates, monkeypatch
):
    outgoing = AsyncMock()
    monkeypatch.setattr(MailProducer, "send_mail_message", outgoing)
    user = await create_user(admin_client)
    login = await request(
        system_app,
        "login",
        {"username": user["username"], "password": user["password"]},
        tenant_id="1",
        ip="127.0.0.111",
    )
    assert login["code"] == 0, login
    target = {"channel": "email", "email": user["email"]}
    sent = await request(system_app, "send-password-reset-code", target)
    assert sent["code"] == 0 and sent["data"] == 6, sent
    message = outgoing.await_args.args[0]
    assert message.to_mails == [user["email"]]
    assert message.account_id > 0 and message.title == "Reset code"
    code = re.search(r"Code (\d{6})", message.content).group(1)
    cached = await cache_state(system_app, user["email"])
    assert cached.hit and "code" not in cached.value and len(cached.value["code_digest"]) == 64
    limited = await request(system_app, "send-password-reset-code", target)
    assert limited["code"] == ErrorCodeConstants.AUTH_RESET_SEND_LIMIT.code
    payload = {**target, "code": code, "password": "Changed123"}
    attempts = await asyncio.gather(
        request(system_app, "reset-password", payload, ip="127.0.0.112"),
        request(system_app, "reset-password", payload, ip="127.0.0.113"),
    )
    assert sorted(item["code"] for item in attempts) == [
        0,
        ErrorCodeConstants.AUTH_RESET_CODE_INVALID.code,
    ], attempts
    fresh = await request(
        system_app,
        "login",
        {"username": user["username"], "password": "Changed123"},
        tenant_id="1",
        ip="127.0.0.114",
    )
    assert fresh["code"] == 0, fresh
    async with AsyncClient(
        transport=ASGITransport(app=system_app), base_url="http://testserver"
    ) as client:
        stale = (
            await client.get(
                "/admin-api/system/auth/get-permission-info",
                headers={"Authorization": "Bearer " + login["data"]["accessToken"]},
            )
        ).json()
    assert stale["code"] != 0


async def test_sms_reset_uses_reset_template_and_rejects_login_code(
    system_app, system_database, admin_client, recovery_templates, monkeypatch
):
    outgoing = AsyncMock()
    monkeypatch.setattr(SmsProducer, "send_sms_message", outgoing)
    user = await create_user(admin_client)
    target = {"channel": "sms", "mobile": user["mobile"]}
    sent = await request(system_app, "send-password-reset-code", target, ip="127.0.0.120")
    assert sent["code"] == 0 and sent["data"] == 4, sent
    outgoing.assert_awaited_once()
    with system_database[2].cursor() as cursor:
        cursor.execute(
            "SELECT code, scene FROM system_sms_code WHERE mobile=%s AND tenant_id='1' ORDER BY id DESC LIMIT 1",
            (user["mobile"],),
        )
        code, scene = cursor.fetchone()
    assert scene == 23 and code != "8888"
    refused = await request(
        system_app,
        "sms-login",
        {"mobile": user["mobile"], "code": code},
        tenant_id="1",
        ip="127.0.0.121",
    )
    assert refused["code"] != 0
    reset = await request(
        system_app,
        "reset-password",
        {**target, "code": code, "password": "Changed123"},
        ip="127.0.0.122",
    )
    assert reset["code"] == 0, reset
    fresh = await request(
        system_app,
        "login",
        {"username": user["username"], "password": "Changed123"},
        tenant_id="1",
        ip="127.0.0.123",
    )
    assert fresh["code"] == 0, fresh


async def test_email_limits_expiry_and_disabled_template(
    system_app, system_database, admin_client, recovery_templates, monkeypatch
):
    outgoing = AsyncMock()
    monkeypatch.setattr(MailProducer, "send_mail_message", outgoing)
    user = await create_user(admin_client)
    target = {"channel": "email", "email": user["email"]}
    assert (await request(system_app, "send-password-reset-code", target, ip="127.0.0.130"))[
        "code"
    ] == 0
    code = re.search(r"Code (\d{6})", outgoing.await_args.args[0].content).group(1)
    wrong = "000000" if code != "000000" else "111111"
    for index in range(5):
        result = await request(
            system_app,
            "reset-password",
            {**target, "code": wrong, "password": "Changed123"},
            ip=f"127.0.0.{131 + index}",
        )
        assert result["code"] == ErrorCodeConstants.AUTH_RESET_CODE_INVALID.code
    assert (
        await request(
            system_app,
            "reset-password",
            {**target, "code": code, "password": "Changed123"},
            ip="127.0.0.136",
        )
    )["code"] != 0
    await cache_state(
        system_app,
        user["email"],
        {"attempts": 0, "expires_at": datetime.now(timezone.utc).timestamp() - 1},
    )
    assert (
        await request(
            system_app,
            "reset-password",
            {**target, "code": code, "password": "Changed123"},
            ip="127.0.0.137",
        )
    )["code"] != 0
    await cache_state(
        system_app,
        user["email"],
        {"issued_at": datetime.now(timezone.utc).timestamp() - 120, "daily_count": 20},
    )
    assert (await request(system_app, "send-password-reset-code", target, ip="127.0.0.138"))[
        "code"
    ] == ErrorCodeConstants.AUTH_RESET_SEND_LIMIT.code
    with system_database[2].cursor() as cursor:
        cursor.execute(
            "UPDATE system_mail_template SET status=0 WHERE id=%s", (recovery_templates["mail"],)
        )
    another = await create_user(admin_client)
    outgoing.reset_mock()
    try:
        disabled = await request(
            system_app,
            "send-password-reset-code",
            {"channel": "email", "email": another["email"]},
            tenant_id="1",
            ip="127.0.0.139",
        )
        assert disabled["code"] == 0 and disabled["data"] == 6, disabled
        outgoing.assert_not_awaited()
        assert (await cache_state(system_app, another["email"])).hit
    finally:
        with system_database[2].cursor() as cursor:
            cursor.execute(
                "UPDATE system_mail_template SET status=1 WHERE id=%s",
                (recovery_templates["mail"],),
            )


async def test_disabled_sms_configuration_keeps_private_response_and_send_limits(
    system_app, system_database, admin_client, recovery_templates, monkeypatch
):
    outgoing = AsyncMock()
    monkeypatch.setattr(SmsProducer, "send_sms_message", outgoing)
    for table, row_id in (
        ("system_sms_template", recovery_templates["sms"]),
        ("system_sms_channel", recovery_templates["channel"]),
    ):
        user = await create_user(admin_client)
        with system_database[2].cursor() as cursor:
            cursor.execute(f"UPDATE {table} SET status=0 WHERE id=%s", (row_id,))
        try:
            failed = await request(
                system_app,
                "send-password-reset-code",
                {"channel": "sms", "mobile": user["mobile"]},
                tenant_id="1",
                ip="127.0.0.150",
            )
            assert failed["code"] == 0 and failed["data"] == 4, failed
            outgoing.assert_not_awaited()
            with system_database[2].cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM system_sms_code WHERE mobile=%s AND tenant_id='1'",
                    (user["mobile"],),
                )
                assert cursor.fetchone()[0] == 1
            limited = await request(
                system_app,
                "send-password-reset-code",
                {"channel": "sms", "mobile": user["mobile"]},
                ip="127.0.0.151",
            )
            assert limited["code"] == ErrorCodeConstants.SMS_CODE_SEND_TOO_FAST.code, limited
        finally:
            with system_database[2].cursor() as cursor:
                cursor.execute(f"UPDATE {table} SET status=1 WHERE id=%s", (row_id,))


async def test_email_code_is_bound_to_tenant_and_account(
    system_app, system_database, admin_client, recovery_templates, monkeypatch
):
    outgoing = AsyncMock()
    monkeypatch.setattr(MailProducer, "send_mail_message", outgoing)
    user = await create_user(admin_client)
    sent = await request(
        system_app,
        "send-password-reset-code",
        {"channel": "email", "email": user["email"]},
        tenant_id="1",
        ip="127.0.0.160",
    )
    assert sent["code"] == 0, sent
    code = re.search(r"Code (\d{6})", outgoing.await_args.args[0].content).group(1)
    package = (
        await admin_client.post(
            "/admin-api/system/tenant/package/create",
            json={"name": "Recovery" + uuid4().hex[:5], "status": 1, "menuIds": []},
        )
    ).json()
    assert package["code"] == 0, package
    tenant = (
        await admin_client.post(
            "/admin-api/system/tenant/create",
            json={
                "name": "Recovery" + uuid4().hex[:5],
                "contactName": "Tenant B",
                "status": 1,
                "packageId": package["data"],
                "expireTime": "2099-01-01T00:00:00",
                "accountCount": 10,
                "username": "admin",
                "password": "TenantB123",
            },
        )
    ).json()
    assert tenant["code"] == 0, tenant
    with system_database[2].cursor() as cursor:
        cursor.execute(
            "UPDATE system_users SET email=%s WHERE tenant_id=%s", (user["email"], tenant["data"])
        )
    denied = await request(
        system_app,
        "reset-password",
        {"channel": "email", "email": user["email"], "code": code, "password": "WrongTenant123"},
        tenant_id=tenant["data"],
        ip="127.0.0.161",
    )
    assert denied["code"] == ErrorCodeConstants.AUTH_RESET_CODE_INVALID.code, denied
    good = await request(
        system_app,
        "reset-password",
        {"channel": "email", "email": user["email"], "code": code, "password": "Changed123"},
        tenant_id="1",
        ip="127.0.0.162",
    )
    assert good["code"] == 0, good


async def test_sms_reset_accepts_only_latest_code_within_attempt_limit(
    system_app, system_database, admin_client, recovery_templates, monkeypatch
):
    monkeypatch.setattr(SmsProducer, "send_sms_message", AsyncMock())
    issued = iter(("1111", "1222"))
    monkeypatch.setattr(SmsCodeServiceImpl, "_normal_code", lambda self: next(issued))
    user = await create_user(admin_client)
    target = {"channel": "sms", "mobile": user["mobile"]}
    first = await request(system_app, "send-password-reset-code", target, ip="127.0.1.1")
    assert first["code"] == 0, first
    with system_database[2].cursor() as cursor:
        cursor.execute(
            "UPDATE system_sms_code SET create_time = create_time - INTERVAL 61 SECOND "
            "WHERE tenant_id='1' AND mobile=%s",
            (user["mobile"],),
        )
    second = await request(system_app, "send-password-reset-code", target, ip="127.0.1.2")
    assert second["code"] == 0, second
    # 旧码 1111 仍在有效期内，但已被新码取代；它与三次随意输入一起占用前 4 次校验机会。
    for index, code in enumerate(("1111", "2000", "3000", "4000")):
        result = await request(
            system_app,
            "reset-password",
            {**target, "code": code, "password": "Changed123"},
            ip=f"127.0.1.{3 + index}",
        )
        assert result["code"] == ErrorCodeConstants.AUTH_RESET_CODE_INVALID.code, result
    reset = await request(
        system_app,
        "reset-password",
        {**target, "code": "1222", "password": "Changed123"},
        ip="127.0.1.7",
    )
    assert reset["code"] == 0, reset
    login = await request(
        system_app,
        "login",
        {"username": user["username"], "password": "Changed123"},
        ip="127.0.1.8",
    )
    assert login["code"] == 0, login


async def test_sms_code_attempts_are_counted_atomically(
    system_app, system_database, admin_client, recovery_templates, monkeypatch
):
    monkeypatch.setattr(SmsProducer, "send_sms_message", AsyncMock())
    monkeypatch.setattr(SmsCodeServiceImpl, "_normal_code", lambda self: "5555")
    user = await create_user(admin_client)
    target = {"channel": "sms", "mobile": user["mobile"]}
    sent = await request(system_app, "send-password-reset-code", target, ip="127.0.1.20")
    assert sent["code"] == 0, sent
    guesses = await asyncio.gather(
        *(
            request(
                system_app,
                "reset-password",
                {**target, "code": "6666", "password": "Changed123"},
                ip=f"127.0.1.{21 + index}",
            )
            for index in range(8)
        )
    )
    assert all(
        item["code"] == ErrorCodeConstants.AUTH_RESET_CODE_INVALID.code for item in guesses
    ), guesses
    with system_database[2].cursor() as cursor:
        cursor.execute(
            "SELECT id FROM system_sms_code WHERE mobile=%s AND tenant_id='1' ORDER BY id DESC LIMIT 1",
            (user["mobile"],),
        )
        code_id = str(cursor.fetchone()[0])
    application, database = system_app.state.application_context, system_app.state.database
    with application.execution(), database.scope():
        async with application.container.get(SystemWorkloadService).scope("system.auth", "1"):
            attempts = await application.container.get(CacheHandler).get(
                SystemCacheKeys.SMS_CODE_ATTEMPTS, code_id
            )
    assert attempts.hit and attempts.value == 8
    exhausted = await request(
        system_app,
        "reset-password",
        {**target, "code": "5555", "password": "Changed123"},
        ip="127.0.1.29",
    )
    assert exhausted["code"] == ErrorCodeConstants.AUTH_RESET_CODE_INVALID.code, exhausted
    kept = await request(
        system_app,
        "login",
        {"username": user["username"], "password": user["password"]},
        ip="127.0.1.30",
    )
    assert kept["code"] == 0, kept


@pytest.mark.parametrize("channel,field,length", [("email", "email", 6), ("sms", "mobile", 4)])
async def test_recovery_does_not_reveal_account_existence(
    system_app, admin_client, recovery_templates, monkeypatch, channel, field, length
):
    mail, sms = AsyncMock(), AsyncMock()
    monkeypatch.setattr(MailProducer, "send_mail_message", mail)
    monkeypatch.setattr(SmsProducer, "send_sms_message", sms)
    monkeypatch.setattr(SmsCodeServiceImpl, "_normal_code", lambda self: "1234")
    user = await create_user(admin_client)
    suffix = uuid4().hex[:10]
    unknown = (
        suffix + "@example.com"
        if channel == "email"
        else "137" + str(int(suffix, 16) % 100_000_000).zfill(8)
    )
    targets = [{"channel": channel, field: value} for value in (user[field], unknown)]
    responses = [
        await request(system_app, "send-password-reset-code", target, ip="127.0.2.10")
        for target in targets
    ]
    for key in ("code", "message", "data"):
        assert responses[0][key] == responses[1][key], responses
    assert responses[0]["code"] == 0 and responses[0]["data"] == length
    (mail if channel == "email" else sms).assert_awaited_once()
    limited = [
        await request(system_app, "send-password-reset-code", target, ip="127.0.2.11")
        for target in targets
    ]
    assert limited[0]["code"] != 0 and limited[0]["code"] == limited[1]["code"], limited
    issued = (
        re.search(r"Code (\d{6})", mail.await_args.args[0].content).group(1)
        if channel == "email"
        else "1234"
    )
    wrong = str((int(issued[0]) + 1) % 10) + issued[1:]
    invalid = [
        await request(
            system_app,
            "reset-password",
            {**target, "code": wrong, "password": "Changed123"},
            ip="127.0.2.12",
        )
        for target in targets
    ]
    assert all(
        result["code"] == ErrorCodeConstants.AUTH_RESET_CODE_INVALID.code for result in invalid
    ), invalid
