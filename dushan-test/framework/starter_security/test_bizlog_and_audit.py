import asyncio
from typing import Annotated

import pytest
from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import insert, select

from framework.starter_di.context.get_bean import get_bean
from framework.starter_security.bizlog.biz_log_service import BizLogService
from framework.starter_security.bizlog.diff_field import DiffField
from framework.starter_security.bizlog.diff_renderer import DiffRenderer
from framework.starter_security.bizlog.log_record import log_record
from framework.starter_security.bizlog.log_record_context import LogRecordContext
from framework.starter_security.bizlog.log_record_spec import LogRecordSpec
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_web.routing.route_policy import RoutePolicy

from .providers import AuditItem, audits


def audit_service(case):
    with case.application.execution():
        return case.application.get_bean(BizLogService)


async def test_http_bizlog_and_existing_orm_core_audit(security_factory):
    router = APIRouter()

    @log_record(
        LogRecordSpec("item", "create", "创建 {{ value }}", "{{ biz_no }}", capture=("value",))
    )
    async def create(value: str = "safe"):
        async with case.database.transaction() as db:
            item = AuditItem(value=value)
            db.add(item)
            await db.flush()
            get_bean(LogRecordContext).put("biz_no", str(item.id))
        return {"created": item.id}

    router.add_api_route("/protected", RoutePolicy()(create))
    async with security_factory(audit=True, router=router) as case:
        token, _ = await case.issue(account_id="author-7")
        response = await case.get(token)
        assert response.json()["created"] > 0
        with case.application.execution():
            async with case.database.read_session() as db:
                item = (await db.execute(select(AuditItem))).scalar_one()
                assert item.creator == item.updater == "author-7"
                row = (await db.execute(select(audits))).one()
                assert row.done and row.outcome == "success"
            async with case.service.authorized(token, RoutePolicy()):
                async with case.database.transaction() as db:
                    await db.execute(insert(AuditItem).values(value="core"))
            async with case.database.read_session() as db:
                item = (
                    await db.execute(select(AuditItem).where(AuditItem.value == "core"))
                ).scalar_one()
                assert item.creator == item.updater == "author-7"
        assert audit_service(case).written == 1


async def test_log_failure_cannot_reverse_committed_business_result(security_factory, monkeypatch):
    async with security_factory(audit=True) as case:
        token, _ = await case.issue()
        service = audit_service(case)

        async def failed(*args):
            raise RuntimeError("private-writer-diagnostic")

        monkeypatch.setattr(service.provider, "finalize", failed)

        @log_record(LogRecordSpec("item", "create", "创建成功", "{{ biz_no }}"))
        async def operation():
            async with case.database.transaction() as db:
                item = AuditItem(value="committed")
                db.add(item)
                await db.flush()
                get_bean(LogRecordContext).put("biz_no", str(item.id))
            return "business-success"

        assert await case.service.run(token, RoutePolicy(), operation) == "business-success"
        assert service.failed == 1 and service.written == 0
        with case.application.execution():
            async with case.database.read_session() as db:
                assert (await db.execute(select(AuditItem.value))).scalar_one() == "committed"


async def test_business_failure_cannot_be_recorded_as_success(security_factory):
    async with security_factory(audit=True) as case:
        token, _ = await case.issue()
        service = audit_service(case)
        failure = ValueError("unlabelled-sensitive-business-detail")

        @log_record(LogRecordSpec("item", "update", "成功", "42", success_condition="{{ true }}"))
        async def operation():
            raise failure

        with pytest.raises(ValueError) as caught:
            await case.service.run(token, RoutePolicy(), operation)
        assert caught.value is failure
        assert service.provider.events[0].result == "failure"
        assert "sensitive" not in service.provider.events[0].action


async def test_cancelled_business_is_finalized_and_renewal_stops(security_factory):
    async with security_factory(audit=True, bizlog_renew_seconds=0.01) as case:
        token, _ = await case.issue()
        service = audit_service(case)
        entered = asyncio.Event()

        @log_record(LogRecordSpec("item", "wait", "完成", "42"))
        async def operation():
            entered.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(case.service.run(token, RoutePolicy(), operation))
        await entered.wait()
        await asyncio.sleep(0.04)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert service.provider.events[0].result == "cancelled"
        assert service.provider.renewals > 0
        assert service.resources()["active_operations"] == 0
        assert case.application.tasks.active_count == 0


async def test_reservation_failure_blocks_business_and_recursion(security_factory, monkeypatch):
    async with security_factory(audit=True) as case:
        token, _ = await case.issue()
        service = audit_service(case)
        calls = []

        @log_record(LogRecordSpec("item", "create", "完成", "42"))
        async def operation():
            calls.append("business")

        async def recursive(operation_info):
            await operation()

        monkeypatch.setattr(service.provider, "reserve", recursive)
        with pytest.raises(SecurityException):
            await case.service.run(token, RoutePolicy(), operation)
        assert calls == [] and service.failed == 1


async def test_same_decorator_uses_each_application_and_safe_projection(security_factory):
    @log_record(LogRecordSpec("profile", "update", "{{ payload }}", "42", capture=("payload",)))
    async def operation(payload):
        return 7

    async with security_factory(audit=True) as first, security_factory(audit=True) as second:
        a, _ = await first.issue(account_id="a")
        b, _ = await second.issue(account_id="b")
        payload = {
            "name": "display",
            "password": "private-password",
            "accessToken": "private-token",
            "cookie": "private-cookie",
        }
        for case, token in ((first, a), (second, b)):
            assert await case.service.run(token, RoutePolicy(), operation, payload) == 7
        for case, expected in ((first, "a"), (second, "b")):
            entry = audit_service(case).provider.events[0]
            assert entry.operation.identity.principal_id == expected
            assert "private-" not in entry.action and "display" in entry.action
            assert "private-" not in repr(entry)


async def test_log_context_nested_and_concurrent_values_are_isolated(security_factory):
    async with security_factory() as case:
        with case.application.execution():
            context = case.application.get_bean(LogRecordContext)
            with context.scope():
                context.put("name", "parent")

                async def child(value):
                    context.put("name", value)
                    await asyncio.sleep(0)
                    return context.values()["name"]

                assert await asyncio.gather(child("a"), child("b")) == ["a", "b"]
                assert context.values()["name"] == "parent"
                with context.scope():
                    assert context.values() == {}
                assert context.values()["name"] == "parent"
            with pytest.raises(RuntimeError):
                context.values()


async def test_diff_metadata_collections_masking_and_bounds(security_factory):
    class Value(BaseModel):
        title: Annotated[str, DiffField("名称")]
        items: Annotated[list[str] | None, DiffField("标签")]
        password: Annotated[str, DiffField("密码", ignore=True)]
        phone: Annotated[str | None, DiffField("手机", formatter="_MASK")]

    async with security_factory(bizlog_max_length=128) as case:
        renderer = DiffRenderer(case.service.settings)
        before = Value(title="old", items=["a", "b", "a"], password="sensitive-old", phone=None)
        after = Value(
            title="new", items=["b", "b", "c"], password="sensitive-new", phone="123456789"
        )
        content = await renderer.render(before, after)
        assert "sensitive" not in content and "密码" not in content
        assert "(x2)" in content and "1*******9" in content
        assert "old" in content and "new" in content
        reordered = before.model_copy(update={"items": ["a", "a", "b"]})
        assert await renderer.render(before, reordered) == ""
        bounded = await renderer.render(before, after.model_copy(update={"title": "x" * 4096}))
        assert len(bounded) <= 128 and bounded.endswith("[差异已截断]")
        with pytest.raises(ValueError):
            DiffRenderer(case.service.settings, (("_MASK", str),))


async def test_debug_response_and_logs_hide_raw_provider_secret(security_factory, monkeypatch):
    async with security_factory(debug=True) as case:
        token, session = await case.issue()
        messages = []
        sink = logger.add(lambda message: messages.append(str(message)), format="{message}")

        async def failed(*args, **kwargs):
            raise RuntimeError("unlabelled-private-token")

        monkeypatch.setattr(case.service.tokens, "resolve", failed)
        try:
            response = await case.get(token)
        finally:
            logger.remove(sink)
        assert response.json()["code"] == 503
        assert "unlabelled-private-token" not in response.text + "".join(messages)
        assert token not in response.text + "".join(messages)
        assert session.account_id not in repr(session)


async def test_cancel_during_reservation_cancels_durable_record(security_factory, monkeypatch):
    async with security_factory(audit=True) as case:
        token, _ = await case.issue()
        service = audit_service(case)
        entered, release = asyncio.Event(), asyncio.Event()
        original = service.provider.reserve
        executed = []

        async def blocked(operation_info):
            reservation = await original(operation_info)
            entered.set()
            await release.wait()
            return reservation

        monkeypatch.setattr(service.provider, "reserve", blocked)

        @log_record(LogRecordSpec("item", "create", "完成", "42"))
        async def operation():
            executed.append(True)

        task = asyncio.create_task(case.service.run(token, RoutePolicy(), operation))
        await entered.wait()
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not executed
        with case.application.execution():
            async with case.database.read_session() as db:
                row = (await db.execute(select(audits))).one()
                assert row.done and row.outcome == "cancelled"
