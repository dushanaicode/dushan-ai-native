import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from framework.starter_job.cron.cron_schedule import CronSchedule
from framework.starter_job.cron.standard_cron_trigger import StandardCronTrigger
from framework.starter_job.exception.job_exception import JobException


@pytest.mark.parametrize("weekday", ["0", "7", "sun"])
def test_sunday_numbering_and_preview(weekday):
    schedule = CronSchedule(f"0 9 * * {weekday}", "UTC")
    start = datetime(2026, 9, 14, tzinfo=UTC)
    assert schedule.preview(start, 2) == [
        datetime(2026, 9, 20, 9, tzinfo=UTC),
        datetime(2026, 9, 27, 9, tzinfo=UTC),
    ]
    trigger = StandardCronTrigger(schedule)
    assert trigger.get_next_fire_time(None, start) == schedule.next(start)


@pytest.mark.parametrize(
    "expression",
    [
        "* * * * * *",
        "0 9 ? * mon",
        "0 0 L * *",
        "0 0 1W * *",
        "0 0 * * mon#2",
        "0 0 * 13 *",
        "0 0 * * 8",
        "0 0 31 2 *",
        "@daily",
    ],
)
def test_invalid_cron_is_an_error(expression):
    with pytest.raises(JobException):
        CronSchedule(expression, "UTC")


def test_ranges_steps_month_end_and_standard_day_or():
    assert CronSchedule("*/15 9-10 * * mon-fri", "UTC").next(
        datetime(2026, 9, 14, 9, 1, tzinfo=UTC)
    ) == datetime(2026, 9, 14, 9, 15, tzinfo=UTC)
    assert CronSchedule("0 0 31 * *", "UTC").next(datetime(2026, 9, 1, tzinfo=UTC)) == datetime(
        2026, 10, 31, tzinfo=UTC
    )
    assert CronSchedule("0 0 1 * mon", "UTC").next(datetime(2026, 9, 2, tzinfo=UTC)) == datetime(
        2026, 9, 7, tzinfo=UTC
    )


def test_dst_gap_and_fold_are_explicit():
    zone = "America/New_York"
    assert CronSchedule("30 2 * * *", zone).next(datetime(2026, 3, 8, 5, tzinfo=UTC)) == datetime(
        2026, 3, 9, 6, 30, tzinfo=UTC
    )
    schedule = CronSchedule("30 1 * * *", zone)
    assert schedule.next(datetime(2026, 11, 1, 4, tzinfo=UTC)) == datetime(
        2026, 11, 1, 5, 30, tzinfo=UTC
    )
    assert schedule.next(datetime(2026, 11, 1, 5, 31, tzinfo=UTC)) == datetime(
        2026, 11, 2, 6, 30, tzinfo=UTC
    )


async def test_real_scheduler_consumes_same_trigger_without_minute_sleep():
    now = datetime.now(UTC)
    due = now.replace(second=0, microsecond=0)
    schedule = CronSchedule("* * * * *", "UTC")
    fired = asyncio.Event()
    scheduler = AsyncIOScheduler(timezone=UTC)
    scheduler.start(paused=True)
    scheduler.add_job(
        fired.set,
        StandardCronTrigger(schedule),
        next_run_time=due,
        misfire_grace_time=120,
        coalesce=True,
        id="cron-proof",
    )
    scheduler.resume()
    try:
        await asyncio.wait_for(fired.wait(), 3)
        assert scheduler.get_job("cron-proof").next_run_time == schedule.next(due)
    finally:
        scheduler.shutdown(wait=False)
        await asyncio.sleep(0)


def test_trigger_coalesces_long_delay_in_bounded_steps():
    schedule = CronSchedule("* * * * *", "UTC")
    trigger = StandardCronTrigger(schedule)
    old = datetime(2020, 1, 1, tzinfo=UTC)
    now = datetime(2026, 9, 14, 12, 34, 20, tzinfo=UTC)
    latest = trigger.get_next_fire_time(old, now)
    assert latest == now.replace(second=0, microsecond=0)
    assert trigger.get_next_fire_time(latest, now) == latest + timedelta(minutes=1)
