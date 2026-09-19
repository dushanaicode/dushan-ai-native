import json

import httpx
import pytest
from fastapi import APIRouter, Request
from opentelemetry import context, trace
from sqlalchemy import Column, Integer, MetaData, String, Table, insert, select

from framework.starter_captcha.definitions.constants.captcha_error_codes import CaptchaErrorCodes
from framework.starter_captcha.exception.captcha_exception import CaptchaException
from framework.starter_di.context.get_bean import get_bean
from framework.starter_monitor.core.monitor_service import MonitorService
from framework.starter_monitor.decorators.auto_trace import AutoTrace
from framework.starter_monitor.decorators.biz_trace import BizTrace


async def test_http_parent_log_correlation_and_sensitive_exception(
    monitor_app, memory_exporters, capfd
):
    router = APIRouter()
    secret = "opaque-private-cookie-ticket-SQL"

    @router.post("/records/{identifier}")
    async def endpoint(identifier: str, request: Request):
        await request.body()
        app.state.bootstrap.logger.info("monitor-business-marker")
        raise CaptchaException(CaptchaErrorCodes.INVALID_INPUT, cause=ValueError(secret))

    app = await monitor_app(routers=[router])
    before = context.get_current()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/records/{secret}?token={secret}",
            headers={
                "traceparent": f"00-{'a' * 32}-{'b' * 16}-01",
                "authorization": f"Bearer {secret}",
                "cookie": f"session={secret}",
            },
            content=secret,
        )
    monitor = app.state.monitor
    assert await monitor.flush()
    spans = memory_exporters[0].get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "POST /records/{identifier}"
    assert span.parent.span_id == int("b" * 16, 16)
    assert span.context.span_id != span.parent.span_id
    assert span.attributes["http.response.status_code"] == 200
    assert span.status.status_code is trace.StatusCode.ERROR
    assert response.headers["trace-id"] == "a" * 32
    assert secret not in span.to_json()
    await app.state.bootstrap.logger.complete()
    output = capfd.readouterr()
    captured = output.out + output.err
    assert "monitor-business-marker" in captured
    assert f"span={span.context.span_id:016x}" in captured
    assert context.get_current() is before


async def test_background_task_and_multiple_applications_are_isolated(
    monitor_app, memory_exporters
):
    a = await monitor_app(app_overrides={"server": {"name": "app-a"}})
    b = await monitor_app(app_overrides={"server": {"name": "app-b"}})

    @AutoTrace()
    async def work():
        return trace.get_current_span().get_span_context().trace_id

    with a.state.application_context.execution():
        with a.state.monitor.span("parent") as parent:
            task = a.state.application_context.tasks.create_task(work)
            background_id = await task
            assert background_id != parent.get_span_context().trace_id
            with b.state.application_context.execution():
                assert get_bean(MonitorService) is b.state.monitor
                second_id = await work()
                assert second_id != parent.get_span_context().trace_id
    await a.state.monitor.flush()
    await b.state.monitor.flush()
    first, second = (output.get_finished_spans() for output in memory_exporters)
    assert len(first) == 2 and len(second) == 1
    assert all(span.parent is None for span in (*first, *second))
    assert all(span.resource.attributes["service.name"] == "app-a" for span in first)
    assert second[0].resource.attributes["service.name"] == "app-b"


async def test_disabled_application_does_not_create_exporter(monitor_app, memory_exporters):
    app = await monitor_app(enabled=False)
    assert app.state.monitor.get_statistics()["state"] == "disabled"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        response = await client.get("/health", headers={"traceparent": "invalid"})
    assert response.status_code == 200
    assert "trace-id" not in response.headers
    assert memory_exporters == []


async def test_query_observer_uses_real_sqlite_and_business_ids_are_unchanged(
    monitor_app, memory_exporters, tmp_path
):
    url = f"sqlite+aiosqlite:///{(tmp_path / 'monitor.sqlite3').as_posix()}"
    app = await monitor_app(
        capture_business_ids=True,
        capture_generated_ids=True,
        app_overrides={
            "config": {
                "models": {
                    "database": {
                        "enabled": True,
                        "sources": [
                            {
                                "name": "primary",
                                "url": url,
                                "role": "primary",
                                "weight": 100,
                                "pool": None,
                                "tls": None,
                            }
                        ],
                        "health_check_enabled": False,
                        "query_template_enabled": True,
                        "query_fingerprint_enabled": True,
                    }
                }
            }
        },
    )
    database = app.state.database
    metadata = MetaData()
    table = Table(
        "monitor_records",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("value", String(100)),
    )
    # 测试建表使用同一SQLite文件，业务操作随后经真实SessionProvider执行。
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)
    await engine.dispose()
    secret = "opaque-SQL-bind-secret"
    with app.state.application_context.execution(), database.scope() as frame:

        @BizTrace(operation_name="save", id_expr="identifier")
        async def save(identifier):
            async with database.transaction() as session:
                await session.execute(insert(table).values(id=identifier, value=secret))
            async with database.read_session() as session:
                result = await session.execute(
                    select(table.c.value).where(table.c.id == identifier)
                )
                return result.scalar_one()

        assert await save(123) == secret
        assert frame.generated_ids == []
    assert await app.state.monitor.flush()
    spans = memory_exporters[0].get_finished_spans()
    parent = next(span for span in spans if span.name == "save")
    queries = [
        span for span in spans if "db.operation.name" in span.attributes and span.parent is not None
    ]
    assert len(queries) >= 2
    assert all(span.parent.span_id == parent.context.span_id for span in queries)
    assert all(span.attributes["db.query.fingerprint"] for span in queries)
    assert all(span.attributes["db.duration_ms"] >= 0 for span in queries)
    assert parent.attributes["biz.id"] == 123
    assert secret not in json.dumps([span.to_json() for span in spans])


async def test_nested_business_trace_observes_generated_ids_without_clearing(
    monitor_app, memory_exporters, tmp_path
):
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.orm import Mapped, mapped_column

    from framework.starter_database.model.base_do import BaseDO

    class GeneratedRow(BaseDO):
        __tablename__ = "monitor_generated_rows"
        metadata = MetaData()
        value: Mapped[str] = mapped_column(String(30))

    url = f"sqlite+aiosqlite:///{(tmp_path / 'generated.sqlite3').as_posix()}"
    app = await monitor_app(
        capture_generated_ids=True,
        app_overrides={
            "config": {
                "models": {
                    "database": {
                        "enabled": True,
                        "health_check_enabled": False,
                        "sources": [
                            {
                                "name": "primary",
                                "url": url,
                                "role": "primary",
                                "weight": 100,
                                "pool": None,
                                "tls": None,
                            }
                        ],
                    }
                }
            }
        },
    )
    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.run_sync(GeneratedRow.__table__.create)
    await engine.dispose()
    db = app.state.database
    with app.state.application_context.execution(), db.scope() as frame:

        @BizTrace(operation_name="child-save")
        async def child():
            async with db.transaction() as session:
                row = GeneratedRow(value="test")
                session.add(row)
                await session.flush()
                return row.id

        @BizTrace(operation_name="outer-save")
        async def outer():
            return await child(), await child()

        ids = await outer()
        assert ids == (1, 2)
        assert frame.generated_ids == [1, 2]
    await app.state.monitor.flush()
    spans = memory_exporters[0].get_finished_spans()
    outer_span = next(span for span in spans if span.name == "outer-save")
    children = [span for span in spans if span.name == "child-save"]
    assert outer_span.attributes["biz.generated_ids"] == ("1", "2")
    assert [span.attributes["biz.generated_ids"] for span in children] == [("1",), ("2",)]


def test_query_observer_binding_does_not_steal_or_clear_other_owner(settings):
    from fixtures.config_factory import ConfigFactory
    from framework.starter_database.config.database_settings import DatabaseSettings
    from framework.starter_database.session.session_provider import SessionProvider

    db = SessionProvider(
        DatabaseSettings.model_validate(ConfigFactory.values()["config"]["models"]["database"])
    )
    first, second = object(), object()
    db.bind_query_observer(first)
    with pytest.raises(ValueError, match="已有消费者"):
        with db.observe_queries(second):
            pytest.fail("不能抢占")
    db.bind_query_observer(None)
    with db.observe_queries(first):
        db.bind_query_observer(second)
    with pytest.raises(ValueError, match="已有消费者"):
        with db.observe_queries(first):
            pytest.fail("不能清掉后来绑定的消费者")
