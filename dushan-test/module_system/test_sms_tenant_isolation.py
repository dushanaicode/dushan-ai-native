from unittest.mock import AsyncMock
from uuid import uuid4

import pymysql
import pytest
import pytest_asyncio
from httpx import URL, ASGITransport, AsyncClient

from framework.starter_cache.public import CacheHandler
from framework.starter_security.public import SecurityRealm, SecurityService
from framework.starter_web.public import RoutePolicy
from module_system.dal.cache.system_cache_key_constants import SystemCacheKeyConstants
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.framework.sms.client.providers.aliyun_sms_client import AliyunSmsClient
from module_system.framework.sms.enums.sms_template_audit_status_enum import (
    SmsTemplateAuditStatusEnum,
)
from module_system.framework.sms.factory.sms_client_factory import SmsClientFactory
from module_system.framework.sms.model.sms_template_resp_dto import SmsTemplateRespDTO
from module_system.mq.producer.sms.sms_producer import SmsProducer
from module_system.service.sms.sms_template_service import SmsTemplateService

pytestmark = pytest.mark.asyncio(loop_scope="module")


async def call(client, method, path, **kwargs):
    result = (await client.request(method, "/admin-api/system/" + path, **kwargs)).json()
    assert result["code"] == 0, result
    return result["data"]


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def tenants(system_app, system_database, admin_client):
    with system_database[2].cursor() as cursor:
        cursor.execute(
            "SELECT id FROM system_menu WHERE permission LIKE 'system:sms:%' OR permission LIKE 'system:user:%'"
        )
        menus = [str(row[0]) for row in cursor.fetchall()]
    package = await call(
        admin_client,
        "POST",
        "tenant/package/create",
        json={"name": "SMS" + uuid4().hex[:8], "status": 1, "menuIds": menus},
    )
    tenant_id = await call(
        admin_client,
        "POST",
        "tenant/create",
        json={
            "name": "SMS" + uuid4().hex[:8],
            "contactName": "Tenant B",
            "status": 1,
            "packageId": package,
            "expireTime": "2099-01-01T00:00:00",
            "accountCount": 20,
            "username": "admin",
            "password": "TenantB123",
        },
    )
    async with AsyncClient(
        transport=ASGITransport(app=system_app), base_url="http://testserver"
    ) as other:
        login = await call(
            other,
            "POST",
            "auth/login",
            json={"username": "admin", "password": "TenantB123"},
            headers={"X-Tenant-Id": tenant_id},
        )
        other.headers["Authorization"] = "Bearer " + login["accessToken"]
        rows = []
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(
                AliyunSmsClient,
                "get_sms_template",
                AsyncMock(
                    return_value=SmsTemplateRespDTO(
                        id="approved", audit_status=SmsTemplateAuditStatusEnum.SUCCESS.code
                    )
                ),
            )
            for label, tenant, client in (("A", "1", admin_client), ("B", tenant_id, other)):
                channel = await call(
                    client,
                    "POST",
                    "sms/channel/create",
                    json={
                        "signature": label,
                        "code": "ALIYUN",
                        "status": 1,
                        "apiKey": "test-account-" + label,
                        "apiSecret": "test-secret-" + label,
                    },
                )
                payload = {
                    "type": 1,
                    "status": 1,
                    "code": "admin-reset-password",
                    "name": label,
                    "content": label + " {code}",
                    "apiTemplateId": "approved-" + label,
                    "channelId": channel,
                }
                template = await call(client, "POST", "sms/template/create", json=payload)
                rows.append(
                    {
                        "tenant": tenant,
                        "client": client,
                        "channel": channel,
                        "template": template,
                        "payload": payload,
                    }
                )
            yield rows


async def cached(system_app, row, *, marker=None):
    application, database = system_app.state.application_context, system_app.state.database
    with application.execution(), database.scope():
        async with application.container.get(SecurityService).authorized(
            row["client"].headers["Authorization"].removeprefix("Bearer "),
            RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT),
        ):
            cache = application.container.get(CacheHandler)
            if marker is not None:
                await cache.set(SystemCacheKeyConstants.SMS_TEMPLATE, "marker", marker)
            template = await application.container.get(
                SmsTemplateService
            ).get_sms_template_by_code_from_cache("admin-reset-password")
            return template, await cache.get(SystemCacheKeyConstants.SMS_TEMPLATE, "marker")


async def test_template_crud_and_constraints_are_tenant_scoped(system_database, tenants):
    first, second = tenants
    for own, foreign in ((first, second), (second, first)):
        client = own["client"]
        page = await call(client, "GET", "sms/template/page", params={"page": 1, "pageSize": 10})
        assert [row["id"] for row in page["items"]] == [own["template"]]
        assert (
            await call(client, "GET", "sms/template/get", params={"id": foreign["template"]})
            is None
        )
        assert (
            await call(client, "GET", "sms/channel/get", params={"id": foreign["channel"]}) is None
        )
        for method, path, payload in (
            (
                "POST",
                "sms/template/create",
                {**own["payload"], "code": "foreign", "channelId": foreign["channel"]},
            ),
            ("PUT", "sms/template/update", {**own["payload"], "id": foreign["template"]}),
        ):
            result = (
                await client.request(method, "/admin-api/system/" + path, json=payload)
            ).json()
            assert result["code"] != 0
        deleted = (
            await client.delete(
                "/admin-api/system/sms/template/delete", params={"id": foreign["template"]}
            )
        ).json()
        assert deleted["code"] == ErrorCodeConstants.SMS_TEMPLATE_NOT_EXISTS.code
        duplicate = (
            await client.post("/admin-api/system/sms/template/create", json=own["payload"])
        ).json()
        assert duplicate["code"] == ErrorCodeConstants.SMS_TEMPLATE_CODE_DUPLICATE.code
    with system_database[2].cursor() as cursor:
        with pytest.raises(pymysql.err.IntegrityError) as foreign_key:
            cursor.execute(
                "UPDATE system_sms_template SET channel_id=%s WHERE id=%s",
                (second["channel"], first["template"]),
            )
        assert foreign_key.value.args[0] == 1452
    temporary = {**first["payload"], "code": "reusable"}
    old = await call(first["client"], "POST", "sms/template/create", json=temporary)
    await call(first["client"], "DELETE", "sms/template/delete", params={"id": old})
    assert await call(first["client"], "POST", "sms/template/create", json=temporary) != old


async def test_template_cache_and_invalidation_do_not_cross_tenants(system_app, tenants):
    first, second = tenants
    for row in tenants:
        value, _ = await cached(system_app, row, marker=row["tenant"])
        assert value.id == int(row["template"])
    await call(
        first["client"],
        "PUT",
        "sms/template/update-status",
        json={"id": first["template"], "status": 0},
    )
    try:
        changed, marker = await cached(system_app, first)
        assert changed.status == 0 and not marker.hit
        unchanged, marker = await cached(system_app, second)
        assert unchanged.status == 1 and marker.value == second["tenant"]
    finally:
        await call(
            first["client"],
            "PUT",
            "sms/template/update-status",
            json={"id": first["template"], "status": 1},
        )


async def test_sms_recovery_uses_each_tenants_account(system_app, tenants, monkeypatch):
    outgoing = AsyncMock()
    monkeypatch.setattr(SmsProducer, "send_sms_message", outgoing)
    mobile = "139" + str(int(uuid4().hex[:8], 16) % 100_000_000).zfill(8)
    username = "recover" + uuid4().hex[:8]
    for row in tenants:
        await call(
            row["client"],
            "POST",
            "user/create",
            json={
                "username": username,
                "nickname": "SMS",
                "password": "Original123",
                "mobile": mobile,
            },
        )
    codes = []
    async with AsyncClient(
        transport=ASGITransport(app=system_app, client=("127.0.0.171", 10000)),
        base_url="http://testserver",
    ) as client:
        for index, row in enumerate(tenants):
            target = {"channel": "sms", "mobile": mobile}
            assert (
                await call(
                    client,
                    "POST",
                    "auth/send-password-reset-code",
                    json=target,
                    headers={"X-Tenant-Id": row["tenant"]},
                )
                == 4
            )
            message = outgoing.await_args.args[0]
            assert message.channel_id == int(row["channel"])
            assert message.api_template_id == row["payload"]["apiTemplateId"]
            code = message.template_params["code"]
            codes.append(code)
            if index == 0:
                denied = (
                    await client.post(
                        "/admin-api/system/auth/reset-password",
                        json={**target, "code": code, "password": "Wrong123"},
                        headers={"X-Tenant-Id": tenants[1]["tenant"]},
                    )
                ).json()
                assert denied["code"] != 0
        for row, code in zip(tenants, codes, strict=True):
            await call(
                client,
                "POST",
                "auth/reset-password",
                json={"channel": "sms", "mobile": mobile, "code": code, "password": "Changed123"},
                headers={"X-Tenant-Id": row["tenant"]},
            )
            login = await call(
                client,
                "POST",
                "auth/login",
                json={"username": username, "password": "Changed123"},
                headers={"X-Tenant-Id": row["tenant"]},
            )
            assert login["tenantId"] == row["tenant"]


async def test_callback_is_bound_to_tenant_channel_and_log(
    system_app, system_database, tenants, monkeypatch
):
    monkeypatch.setattr(SmsProducer, "send_sms_message", AsyncMock())
    urls = []
    logs = []
    for row in tenants:
        urls.append(
            await call(
                row["client"], "GET", "sms/channel/callback-url", params={"id": row["channel"]}
            )
        )
        assert set(URL(urls[-1]).params) == {"token"}
        logs.append(
            await call(
                row["client"],
                "POST",
                "sms/template/send-sms",
                json={
                    "mobile": "13800138000",
                    "templateCode": "admin-reset-password",
                    "templateParams": {"code": "1234"},
                },
            )
        )
    extra_channel = await call(
        tenants[0]["client"],
        "POST",
        "sms/channel/create",
        json={
            "signature": "Other",
            "code": "ALIYUN",
            "status": 1,
            "apiKey": "test-other",
            "apiSecret": "test-other",
        },
    )
    extra_url = await call(
        tenants[0]["client"], "GET", "sms/channel/callback-url", params={"id": extra_channel}
    )
    # 模拟进程刚启动，回执处理不能依赖之前发送时创建的客户端。
    with system_app.state.application_context.execution():
        factory = system_app.state.application_context.container.get(SmsClientFactory)
        await factory.close()
        factory.channel_id_clients.clear()

    def body(log_id):
        return [
            {
                "success": True,
                "err_code": "DELIVERED",
                "err_msg": "ok",
                "phone_number": "13800138000",
                "report_time": "2026-09-22T00:00:00",
                "biz_id": "test",
                "out_id": log_id,
            }
        ]

    async with AsyncClient(
        transport=ASGITransport(app=system_app), base_url="http://testserver"
    ) as client:
        tampered = URL(urls[0]).copy_set_param("tenantId", tenants[1]["tenant"])
        assert (await client.post(tampered, json=body(logs[0]))).json()["code"] != 0
        token = URL(urls[0]).params["token"]
        invalid_token = token[:-1] + ("0" if token[-1] != "0" else "1")
        assert (
            await client.post(
                URL(urls[0]).copy_set_param("token", invalid_token), json=body(logs[0])
            )
        ).json()["code"] != 0
        assert (await client.post(urls[1], json=body(logs[0]))).json()["code"] != 0
        assert (await client.post(extra_url, json=body(logs[0]))).json()["code"] != 0
        for url, log_id in zip(urls, logs, strict=True):
            assert (await client.post(url, json=body(log_id))).json()["code"] == 0
            assert (await client.post(url, json=body(log_id))).json()["code"] == 0
    foreign_url = (
        await tenants[0]["client"].get(
            "/admin-api/system/sms/channel/callback-url", params={"id": tenants[1]["channel"]}
        )
    ).json()
    assert foreign_url["code"] == ErrorCodeConstants.SMS_CHANNEL_NOT_EXISTS.code
    with system_database[2].cursor() as cursor:
        cursor.execute(
            "SELECT tenant_id,channel_id,receive_status FROM system_sms_log WHERE id IN (%s,%s) ORDER BY id",
            logs,
        )
        assert cursor.fetchall() == tuple(
            (row["tenant"], int(row["channel"]), 10) for row in tenants
        )
