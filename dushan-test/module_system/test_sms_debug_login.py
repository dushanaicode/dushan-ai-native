from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from framework.common.enums import ApplicationEnvironmentEnum
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.sms.sms_code_service import SmsCodeService
from module_system.service.sms.sms_send_service_impl import SmsSendServiceImpl
from server.starter_server import StarterServer

pytestmark = pytest.mark.asyncio(loop_scope="module")
MOBILES = ("13800001001", "13800001002", "13800001003")


@pytest.fixture(scope="module")
def sms_captcha_overrides():
    return {"debug_enabled": True, "debug_mobiles": list(MOBILES)}


async def test_debug_sms_requires_development_whitelist_send_and_single_use(
    system_app, system_database, admin_client, monkeypatch, tmp_path
):
    application = system_app.state.application_context
    with application.execution():
        service = application.container.get(SmsCodeService)
        assert service.environment is ApplicationEnvironmentEnum.DEVELOPMENT
    sender = AsyncMock(return_value=1)
    monkeypatch.setattr(SmsSendServiceImpl, "send_single_sms", sender)
    mobiles = MOBILES
    for mobile in mobiles:
        created = (
            await admin_client.post(
                "/admin-api/system/user/create",
                json={
                    "username": "s" + uuid4().hex[:10],
                    "nickname": "SMS debug test",
                    "password": "Password123",
                    "mobile": mobile,
                },
            )
        ).json()
        assert created["code"] == 0, created

    counter = 30

    async def post(path, payload, *, tenant_id="1"):
        nonlocal counter
        counter += 1
        transport = ASGITransport(app=system_app, client=(f"127.0.0.{counter}", 10000))
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            return (
                await client.post(
                    "/admin-api/system/auth/" + path,
                    json=payload,
                    headers={"X-Tenant-Id": tenant_id},
                )
            ).json()

    payload = {"mobile": mobiles[0], "code": "8888"}
    missing = await post("sms-login", payload)
    assert missing["code"] == ErrorCodeConstants.SMS_CODE_NOT_FOUND.code
    for mobile in mobiles:
        sent = await post("send-sms-code", {"mobile": mobile, "scene": 21}, tenant_id="1")
        assert sent["code"] == 0 and type(sent["data"]) is int and sent["data"] == 4, sent
    sender.assert_not_awaited()

    package = (
        await admin_client.post(
            "/admin-api/system/tenant/package/create",
            json={"name": "SMS" + uuid4().hex[:8], "status": 1, "menuIds": []},
        )
    ).json()
    assert package["code"] == 0, package
    tenant = (
        await admin_client.post(
            "/admin-api/system/tenant/create",
            json={
                "name": "SMS" + uuid4().hex[:8],
                "contactName": "SMS tenant B",
                "status": 1,
                "packageId": package["data"],
                "expireTime": "2099-01-01T00:00:00",
                "accountCount": 10,
                "username": "admin",
                "password": "Password123",
            },
        )
    ).json()
    assert tenant["code"] == 0, tenant
    with system_database[2].cursor() as cursor:
        cursor.execute(
            "UPDATE system_users SET mobile=%s WHERE tenant_id=%s", (mobiles[0], tenant["data"])
        )
    foreign = await post("sms-login", {**payload}, tenant_id=tenant["data"])
    assert foreign["code"] == ErrorCodeConstants.SMS_CODE_NOT_FOUND.code, foreign

    login = await post("sms-login", payload)
    assert login["code"] == 0 and login["data"]["tenantId"] == "1", login
    reused = await post("sms-login", payload)
    assert reused["code"] == ErrorCodeConstants.SMS_CODE_USED.code

    unused = {"mobile": mobiles[1], "code": "8888"}
    source = system_app.state.bootstrap.base_dir / "application.yaml"
    for offset, (name, environment, overrides) in enumerate(
        (
            ("off", "dev", {"debug_enabled": False}),
            ("empty", "dev", {"debug_mobiles": []}),
            ("production", "prod", {}),
        )
    ):
        values = yaml.safe_load(source.read_text(encoding="utf-8"))
        values["config"]["models"]["sms_captcha"].update(overrides)
        values["config"]["models"]["database"]["snowflake_machine_id"] = 914
        values["banner"]["enabled"] = False
        if environment == "prod":
            values["server"].update(debug=False, reload=False, docs_enabled=False)
        folder = tmp_path / name
        folder.mkdir()
        (folder / "application.yaml").write_text(yaml.safe_dump(values), encoding="utf-8")
        if environment == "prod":
            (folder / "application-prod.yaml").write_text("{}\n", encoding="utf-8")
        other = StarterServer.create_app(base_dir=folder, app_env=environment, environ={})
        async with other.router.lifespan_context(other):
            async with AsyncClient(
                transport=ASGITransport(app=other, client=(f"127.0.0.{90 + offset}", 10000)),
                base_url="http://testserver",
            ) as client:
                for supplied_code in ("8888", "8888 ", "８８８８"):
                    denied = (
                        await client.post(
                            "/admin-api/system/auth/sms-login",
                            json={**unused, "code": supplied_code},
                            headers={"X-Tenant-Id": "1"},
                        )
                    ).json()
                    assert denied["code"] == ErrorCodeConstants.SMS_CODE_NOT_CORRECT.code, denied

    reset = await post("reset-password", {**unused, "password": "Different123"})
    assert reset["code"] == ErrorCodeConstants.AUTH_RESET_CODE_INVALID.code, reset
    reenabled = await post("sms-login", unused)
    assert reenabled["code"] == 0, reenabled

    with system_database[2].cursor() as cursor:
        cursor.execute(
            "UPDATE system_sms_code SET create_time='2000-01-01' WHERE tenant_id='1' AND mobile=%s",
            (mobiles[2],),
        )
    expired = await post("sms-login", {"mobile": mobiles[2], "code": "8888"}, tenant_id="1")
    assert expired["code"] == ErrorCodeConstants.SMS_CODE_EXPIRED.code


async def test_normal_sms_never_generates_reserved_debug_code(
    system_app, admin_client, monkeypatch
):
    import module_system.service.sms.sms_code_service_impl as sms_module

    application = system_app.state.application_context
    with application.execution():
        service = application.container.get(SmsCodeService)
        settings = service.settings
    sender = AsyncMock(return_value=1)
    monkeypatch.setattr(SmsSendServiceImpl, "send_single_sms", sender)
    with application.execution(), monkeypatch.context() as controlled:
        controlled.setattr(
            sms_module.secrets, "randbelow", lambda count: 8888 - settings.begin_code
        )
        assert service._normal_code() == "8889"
    mobile = "13800001004"
    result = (
        await admin_client.post(
            "/admin-api/system/user/create",
            json={
                "username": "s" + uuid4().hex[:10],
                "nickname": "Normal SMS",
                "password": "Password123",
                "mobile": mobile,
            },
        )
    ).json()
    assert result["code"] == 0, result
    async with AsyncClient(
        transport=ASGITransport(app=system_app, client=("127.0.0.80", 10000)),
        base_url="http://testserver",
    ) as client:
        result = (
            await client.post(
                "/admin-api/system/auth/send-sms-code",
                json={"mobile": mobile, "scene": 21},
                headers={"X-Tenant-Id": "1"},
            )
        ).json()
    assert result["code"] == 0 and result["data"] == 4, result
    sender.assert_awaited_once()
    assert sender.await_args.args[0].template_params["code"] != "8888"
