import asyncio

import httpx
import pytest
from fastapi import Depends
from sqlalchemy import literal, select
from starlette.responses import StreamingResponse

from fixtures.public_web_app import create_public_app
from fixtures.starter_steps import StarterSteps
from framework.common.page.core.data_paginator import DataPaginator
from framework.starter_database.decorators.transactional import transactional
from framework.starter_database.pagination.sql_paginator import SqlPaginator
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.context.get_bean import get_bean
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_di.definitions.enums.container_state_enum import ContainerStateEnum


def app_values(settings):
    values = settings.model_dump(mode="json")
    for source, original in zip(values["sources"], settings.sources):
        source["url"] = original.url.get_secret_value()
    return {"config": {"models": {"database": values}}, "banner": {"enabled": False}}


@pytest.mark.parametrize("scan", [True, False])
async def test_application_explicit_database_definitions_and_real_http(
    database_settings, config_dir, scan
):
    values = app_values(database_settings)
    values["scanner"] = {"enabled": scan}
    app = create_public_app(
        base_dir=config_dir(values), environ={}, steps=StarterSteps.without_tenant()
    )

    @app.get("/database")
    async def route(
        database=Depends(DiDependency(SessionProvider)),
        paginator=Depends(DiDependency(SqlPaginator)),
        memory_paginator=Depends(DiDependency(DataPaginator)),
    ):
        assert type(memory_paginator) is DataPaginator
        assert type(paginator) is SqlPaginator
        async with database.read_session() as session:
            page = await paginator.paginate_query(session, select(literal(7)))
            assert page.total == 1
            return {"value": page.items[0]}

    async with app.router.lifespan_context(app):
        database = app.state.database
        assert database.is_ready
        context = app.state.application_context
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as client:
            assert (await client.get("/database")).json() == {"value": 7}
        assert database.get_metrics()["pools"]["primary"]["leases"] == 0
    assert app.state.database is None and not database.is_ready
    assert context.container.state is ContainerStateEnum.CLOSED


async def test_transaction_decorator_uses_current_application(database_settings, config_dir):
    app = create_public_app(
        base_dir=config_dir(app_values(database_settings)),
        environ={},
        steps=StarterSteps.without_tenant(),
    )

    @transactional
    async def operation():
        database = get_bean(SessionProvider)
        async with database.read_session() as session:
            return await session.scalar(select(literal(8)))

    async with app.router.lifespan_context(app):
        assert await app.state.application_context.tasks.run(operation) == 8


async def test_streaming_response_can_read_database_in_framework_child_task(
    database_settings, config_dir
):
    app = create_public_app(
        steps=StarterSteps.without_tenant(),
        base_dir=config_dir(app_values(database_settings)),
        environ={},
        engine="uvicorn",
    )

    @app.get("/stream")
    async def route(database=Depends(DiDependency(SessionProvider))):
        async def body():
            async with database.read_session() as session:
                yield str(await session.scalar(select(literal(9))))

        return StreamingResponse(body())

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as client:
            assert (await client.get("/stream")).text == "9"


async def test_after_commit_background_work_created_during_application_drain(
    database_settings, config_dir
):
    app = create_public_app(
        base_dir=config_dir(app_values(database_settings)),
        environ={},
        steps=StarterSteps.without_tenant(),
    )
    admitted, release = asyncio.Event(), asyncio.Event()
    called = []
    async with app.router.lifespan_context(app):
        application = app.state.application_context
        database = app.state.database

        async def callback():
            async with database.read_session() as session:
                called.append(await session.scalar(select(literal(10))))

        async def work():
            async with database.transaction():
                database.after_commit(callback, required=False)
                admitted.set()
                await release.wait()

        task = application.tasks.create_task(work)
        await admitted.wait()
        draining = asyncio.create_task(application.drain())
        await asyncio.sleep(0)
        release.set()
        await task
        await draining
    assert called == [10]
