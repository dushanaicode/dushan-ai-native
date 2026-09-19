from __future__ import annotations

import asyncio
import inspect
import socket

import httpx
import pytest
import uvicorn
from fastapi import APIRouter, Depends, Request
from loguru import logger
from pydantic import BaseModel, Field, SecretStr

from fixtures.config_factory import ConfigFactory
from framework.common.exception.exceptions.illegal_argument_exception import (
    IllegalArgumentException,
)
from framework.starter_monitor.config.monitor_settings import MonitorSettings
from framework.starter_monitor.core.monitor_service import MonitorService
from framework.starter_protection.definitions.constants.protection_error_codes import (
    ProtectionErrorCodes as Codes,
)
from framework.starter_protection.idempotent.idempotency_rule import IdempotencyRule
from framework.starter_protection.integration.monitor_protection_observer import (
    MonitorProtectionObserver,
)
from framework.starter_protection.ratelimiter.rate_limit_rule import RateLimitRule
from framework.starter_protection.subject.protection_subject import ProtectionSubject
from framework.starter_protection.web.distributed_lock import distributed_lock
from framework.starter_protection.web.idempotent import idempotent
from framework.starter_protection.web.rate_limit import rate_limit
from framework.starter_web.context.request_context import RequestContext


class Input(BaseModel):
    quantity: int = Field(ge=1)
    password: SecretStr


async def verified_identity(request: Request):
    # 测试中的服务端会话映射，主体不来自客户端直接声明的 account/tenant 头。
    account = {"session-a": "account-a", "session-b": "account-b"}[request.headers["authorization"]]
    return ProtectionSubject(kind="principal", identifier=account, tenant_id="tenant-server")


def identity_from_validated_dependency(bound):
    return bound.arguments["identity"]


async def test_web_validation_repeat_and_trusted_subject(protection_app):
    router = APIRouter()
    calls = []

    @router.post("/submit/{item_id}")
    @idempotent(
        "web.submit", parameters=("item_id", "payload"), subject=identity_from_validated_dependency
    )
    async def submit(
        item_id: int,
        payload: Input,
        req: Request,
        identity: ProtectionSubject = Depends(verified_identity),
    ):
        calls.append((item_id, identity.identifier))
        return {"code": 0, "data": {"id": item_id, "quantity": payload.quantity}}

    app = await protection_app(routers=[router])
    assert "payload" in inspect.signature(submit).parameters
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        auth = {"authorization": "session-a"}
        invalid = await client.post(
            "/submit/7", json={"quantity": 0, "password": "body-secret"}, headers=auth
        )
        assert invalid.status_code == 200 and invalid.json()["code"] == 422 and calls == []
        first = await client.post(
            "/submit/7", json={"quantity": 2, "password": "body-secret"}, headers=auth
        )
        # x-tenant-id 不在这里用于伪造：starter_tenant 的 TenantSelectorMiddleware 会对
        # 任何携带该请求头的请求无条件返回 403（早于路由分发），伪造租户头的场景应由
        # starter_tenant/starter_web 侧的测试验证；这里只验证服务端可信身份解析不受
        # x-user-id 这类伪造头影响。
        duplicate = await client.post(
            "/submit/7",
            json={"password": "body-secret", "quantity": "2"},
            headers={**auth, "x-user-id": "forged-user"},
        )
        assert first.json() == {"code": 0, "data": {"id": 7, "quantity": 2}}
        assert duplicate.status_code == 200 and duplicate.json()["code"] == Codes.DUPLICATE.code
        assert duplicate.json()["error"]["retryAfter"] > 0
        second_user = await client.post(
            "/submit/7",
            json={"quantity": 2, "password": "body-secret"},
            headers={"authorization": "session-b"},
        )
        assert second_user.json()["code"] == 0
        changed_password = await client.post(
            "/submit/7", json={"quantity": 2, "password": "other-secret"}, headers=auth
        )
        assert changed_password.json()["code"] == 0
    assert len(calls) == 3


async def test_web_rate_retry_after_and_body_unconsumed(protection_app, monkeypatch):
    router = APIRouter()
    rule = RateLimitRule(algorithm="fixed", capacity=1, window_ms=1800)

    @router.post("/rate")
    @rate_limit("web.rate", rules=(rule,))
    async def endpoint(req: Request, payload: Input):
        return {"quantity": payload.quantity}

    app = await protection_app(routers=[router])
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        invalid = await client.post("/rate", json={"quantity": "bad", "password": "secret"})
        assert invalid.json()["code"] == 422
        assert (await client.post("/rate", json={"quantity": 2, "password": "secret"})).json() == {
            "quantity": 2
        }
        rejected = await client.post(
            "/rate",
            json={"quantity": 2, "password": "secret"},
            headers={"x-forwarded-for": "203.0.113.2"},
        )
        assert rejected.status_code == 200
        assert rejected.json()["code"] == Codes.RATE_LIMITED.code
        assert rejected.headers["retry-after"] == str(rejected.json()["error"]["retryAfter"])
        assert rejected.headers["retry-after"] in ("1", "2")

    # 已完成参数校验后直接调用装饰器；若包装器重新消费请求体，此断言会立即失败。
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/rate",
            "headers": [],
            "app": app,
            "client": ("new-peer", 10),
        }
    )

    async def forbidden_body(self):
        pytest.fail("保护装饰器不能重新读取请求体")

    monkeypatch.setattr(Request, "body", forbidden_body)
    with (
        app.state.application_context.execution(),
        RequestContext.bind(request, "direct-test", "198.51.100.2"),
    ):
        assert await endpoint(request, Input(quantity=2, password="secret")) == {"quantity": 2}


async def test_same_decorated_route_isolated_between_apps(protection_app, namespace):
    router = APIRouter()
    rule = RateLimitRule(algorithm="fixed", capacity=1, window_ms=2000)

    @rate_limit("same.function", rules=(rule,))
    async def endpoint(request: Request):
        await asyncio.sleep(0.01)
        return {"success": True}

    router.get("/same")(endpoint)
    one = await protection_app(routers=[router])
    two = await protection_app(prefix=namespace + "_two", routers=[router])
    async with (
        httpx.AsyncClient(transport=httpx.ASGITransport(one), base_url="http://one") as a,
        httpx.AsyncClient(transport=httpx.ASGITransport(two), base_url="http://two") as b,
    ):
        first = await asyncio.gather(a.get("/same"), b.get("/same"))
        assert [response.json() for response in first] == [{"success": True}] * 2
        repeated = await asyncio.gather(a.get("/same"), b.get("/same"))
        assert all(response.json()["code"] == Codes.RATE_LIMITED.code for response in repeated)


async def test_web_lock_idempotent_stacking_and_original_business_error(protection_app):
    router = APIRouter()
    entered, release = asyncio.Event(), asyncio.Event()
    rule = IdempotencyRule(
        mode="delete_on_complete", ttl_ms=3000, max_lifetime_ms=3000, failure_action="release"
    )

    @router.post("/work/{value}")
    @idempotent("work", parameters=("value",), rule=rule, release_on=(IllegalArgumentException,))
    @distributed_lock("work", parameters=("value",))
    async def work(request: Request, value: int):
        if value == 9:
            raise IllegalArgumentException(msg="业务参数拒绝")
        entered.set()
        await release.wait()
        return {"value": value}

    app = await protection_app(routers=[router])
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        running = asyncio.create_task(client.post("/work/1"))
        await entered.wait()
        duplicate = await client.post("/work/1")
        assert duplicate.json()["code"] == Codes.DUPLICATE.code
        release.set()
        assert (await running).json() == {"value": 1}
        assert (await client.post("/work/1")).json() == {"value": 1}
        for _ in range(2):
            invalid = await client.post("/work/9")
            assert invalid.json()["code"] == 400 and invalid.json()["message"] == "业务参数拒绝"


async def test_disabled_app_runs_without_cache_and_lookup(protection_app):
    router = APIRouter()

    @router.get("/disabled")
    @rate_limit("disabled")
    @idempotent("disabled", parameters=())
    @distributed_lock("disabled", parameters=())
    async def endpoint(request: Request):
        return {"success": True}

    app = await protection_app(
        routers=[router],
        overrides={
            "di": {"lookup_enabled": False},
            "config": {"models": {"cache": {"enabled": False}, "protection": {"enabled": False}}},
        },
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        for _ in range(2):
            assert (await client.get("/disabled")).json() == {"success": True}
    with app.state.application_context.execution():
        assert await app.state.protection.health() == "disabled"


async def test_missing_cache_or_namespace_collision_fails_startup(protection_app):
    with pytest.raises(Exception):
        await protection_app(overrides={"config": {"models": {"cache": {"enabled": False}}}})
    with pytest.raises(Exception):
        await protection_app(
            overrides={
                "config": {
                    "models": {
                        "captcha": {"enabled": True},
                        "protection": {"key_prefix": "captcha:overlap"},
                    }
                }
            }
        )


async def test_optional_monitor_exports_actual_protection_events(services, subject):
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    values = ConfigFactory.values()["config"]["models"]["monitor"]
    values.update(
        enabled=True,
        service_name="protection-test",
        service_version="test",
        sampler="always_on",
        exporter="none",
    )
    monitor = MonitorService(MonitorSettings.model_validate(values))
    exporter = InMemorySpanExporter()
    await monitor.open(diagnostic_logger=logger, exporter=exporter)
    try:
        service = await services(observer=MonitorProtectionObserver(monitor))
        assert (
            await service.rate_limiter.acquire(
                "private-operation", subject, {"password": "raw-sensitive"}
            )
        ).allowed
        async with service.locks.hold("private-operation", subject):
            pass
        async with service.idempotency.guard("private-operation", subject, 5):
            pass
        assert await monitor.flush()
        spans = exporter.get_finished_spans()
        names = [span.name for span in spans]
        assert "protection.rate_limit.acquire.acquired" in names
        assert "protection.lock.acquire.acquired" in names
        assert "protection.idempotency.acquire.acquired" in names
        assert not any(
            "raw-sensitive" in str(span.attributes) or "private-operation" in span.name
            for span in spans
        )
    finally:
        await monitor.close()
    assert monitor._spans == set()


async def test_real_tcp_web_request(protection_app):
    router = APIRouter()

    @router.post("/tcp")
    @idempotent("tcp", parameters=("payload",))
    async def endpoint(request: Request, payload: Input):
        return {"quantity": payload.quantity}

    app = await protection_app(routers=[router])
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            app, host="127.0.0.1", port=port, lifespan="off", log_config=None, access_log=False
        )
    )
    task = asyncio.create_task(server.serve(sockets=[sock]))
    try:
        async with asyncio.timeout(3):
            while not server.started:
                await asyncio.sleep(0.01)
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}") as client:
            first = await client.post("/tcp", json={"quantity": 3, "password": "secret"})
            duplicate = await client.post("/tcp", json={"quantity": 3, "password": "secret"})
            assert first.json() == {"quantity": 3}
            assert duplicate.status_code == 200 and duplicate.json()["code"] == Codes.DUPLICATE.code
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, 3)
        sock.close()
