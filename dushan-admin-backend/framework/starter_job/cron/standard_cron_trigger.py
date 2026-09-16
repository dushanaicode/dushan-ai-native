from datetime import timedelta

from apscheduler.triggers.base import BaseTrigger

from framework.starter_job.cron.cron_schedule import CronSchedule


class StandardCronTrigger(BaseTrigger):
    """调度和预览共用 CronSchedule；延迟时直接跳到最近一次应触发点，合并有界。"""

    def __init__(self, schedule: CronSchedule):
        self.schedule = schedule

    def get_next_fire_time(self, previous_fire_time, now):
        if previous_fire_time is None:
            return self.schedule.next(now - timedelta(microseconds=1))
        candidate = self.schedule.next(previous_fire_time)
        if candidate < now:
            latest = self.schedule.previous(now)
            if latest > candidate:
                return latest
        return candidate
