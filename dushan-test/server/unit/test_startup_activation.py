import asyncio
from contextlib import asynccontextmanager

import httpx
import pytest

from fixtures.public_web_app import create_public_app
from framework.starter_di.context.application_state_enum import ApplicationStateEnum
from framework.starter_web.banner.banner_application_runner import BannerApplicationRunner
from server.bootstrap.bootstrapper import BootstrapError
from server.bootstrap.step_registry import APP_BOOTSTRAP_STEPS, BootstrapStepSpec


async def test_activation_blocks_readiness_banner_and_lifespan_completion(config_dir, monkeypatch):
    events = []
    entered, release, started, stop = (asyncio.Event() for _ in range(4))

    @asynccontextmanager
    async def resource(ctx):
        async def mq():
            assert ctx.definitions.application_context.state is ApplicationStateEnum.READY
            assert not ctx.ready
            events.append("mq-start")
            entered.set()
            await release.wait()
            events.append("mq-ready")

        async def job():
            assert events[-1] == "mq-ready" and not ctx.ready
            events.append("job-ready")

        ctx.before_ready.extend((("MQ", mq), ("Job", job)))
        try:
            yield
        finally:
            events.append("closed")

    async def banner(self, info):
        assert app.state.bootstrap.ready
        events.append("banner")

    monkeypatch.setattr(BannerApplicationRunner, "print_startup_complete", banner)
    app = create_public_app(
        base_dir=config_dir(),
        environ={},
        steps=(*APP_BOOTSTRAP_STEPS, BootstrapStepSpec("激活", resource)),
    )

    async def run():
        async with app.router.lifespan_context(app):
            events.append("lifespan-ready")
            started.set()
            await stop.wait()

    task = asyncio.create_task(run())
    try:
        async with asyncio.timeout(20):
            await entered.wait()
            assert not started.is_set() and "banner" not in events
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url="http://test"
            ) as client:
                assert (await client.get("/health")).status_code == 503
            release.set()
            await started.wait()
        assert events == ["mq-start", "mq-ready", "job-ready", "banner", "lifespan-ready"]
    finally:
        release.set()
        stop.set()
        await task
    assert not app.state.bootstrap.ready and events[-1] == "closed"


@pytest.mark.parametrize(
    "failure",
    [
        OSError("subscription failed"),
        TimeoutError("activation timed out"),
        asyncio.CancelledError(),
    ],
)
async def test_activation_failure_or_cancel_never_announces_ready_and_cleans_resources(
    config_dir, monkeypatch, failure
):
    events = []

    @asynccontextmanager
    async def resource(ctx):
        async def activate():
            events.append("activate")
            raise failure

        async def quiesce():
            events.append("quiesce")

        ctx.before_ready.append(("MQ", activate))
        ctx.before_drain.append(quiesce)
        try:
            yield
        finally:
            events.append("closed")

    async def banner(self, info):
        events.append("banner")

    monkeypatch.setattr(BannerApplicationRunner, "print_startup_complete", banner)
    app = create_public_app(
        base_dir=config_dir(),
        environ={},
        steps=(*APP_BOOTSTRAP_STEPS, BootstrapStepSpec("激活", resource)),
    )
    expected = (
        asyncio.CancelledError if isinstance(failure, asyncio.CancelledError) else BootstrapError
    )
    with pytest.raises(expected) as error:
        async with app.router.lifespan_context(app):
            pytest.fail("激活失败不能进入服务阶段")
    if expected is BootstrapError:
        assert error.value.__cause__ is failure
    assert not app.state.bootstrap.ready
    assert events == ["activate", "quiesce", "closed"]
    assert app.state.application_context is None
