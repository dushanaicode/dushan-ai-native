import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from framework.starter_job.cron.cron_schedule import CronSchedule
from server.starter_server import create_app


async def wait_runs(case, count):
    async with asyncio.timeout(5):
        while len(case.probe.runs) < count:
            await asyncio.sleep(0.01)


async def test_real_scheduler_trigger_uses_preview_time(job_case, monkeypatch):
    case = job_case
    actual = datetime.now(UTC)
    due = CronSchedule("* * * * *", "UTC").next(actual)
    with case.app.state.application_context.execution():
        await case.service.save(case.definition(cron="* * * * *"))

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            value = due + timedelta(milliseconds=50)
            return value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)

    monkeypatch.setattr("apscheduler.schedulers.base.datetime", Clock)
    monkeypatch.setattr("framework.starter_job.core.job_runtime.datetime", Clock)
    monkeypatch.setattr("framework.starter_job.core.job_invoker.datetime", Clock)
    case.runtime.scheduler.wakeup()
    await wait_runs(case, 1)
    async with case.engine.connect() as connection:
        request = await connection.scalar(select(case.module.RequestRow.spec))
    assert datetime.fromisoformat(request["scheduled_at"].replace("Z", "+00:00")) == due


async def test_startup_rebuild_coalesces_once_and_checkpoint_survives(job_case, monkeypatch):
    case = job_case
    due = CronSchedule("* * * * *", "UTC").next(datetime.now(UTC))

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            # 冻结在同一个 due 窗口内：save→两次 reconcile→关闭→新 app reconcile
            # 全程发生在真实分钟边界之内，避免真实墙钟推进产生合法的新到期请求，
            # 与断言"只合并补跑一次"的前提保持一致。
            value = due + timedelta(milliseconds=50)
            return value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)

    monkeypatch.setattr("apscheduler.schedulers.base.datetime", Clock)
    monkeypatch.setattr("framework.starter_job.core.job_runtime.datetime", Clock)
    monkeypatch.setattr("framework.starter_job.core.job_invoker.datetime", Clock)
    definition = case.definition(
        cron="* * * * *", effective_at=datetime.now(UTC) - timedelta(days=5)
    )
    with case.app.state.application_context.execution():
        await case.service.save(definition)
    await wait_runs(case, 1)
    with case.app.state.application_context.execution():
        await case.runtime.reconcile()
        await case.runtime.reconcile()
    await case.runtime.close()
    other = create_app(base_dir=case.config_path, environ={})
    async with other.router.lifespan_context(other):
        assert other.state.job.owner
        with other.state.application_context.execution():
            await other.state.job.reconcile()
        async with case.engine.connect() as connection:
            assert (
                await connection.scalar(select(func.count()).select_from(case.module.RequestRow))
                == 1
            )
