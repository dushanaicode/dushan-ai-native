from abc import ABC, abstractmethod

from framework.starter_job.definitions.enums.job_state import JobState


class JobHandler(ABC):
    """每次尝试从 DI 解析新实例；同步 execute 在受管线程中完成。"""

    @abstractmethod
    def execute(self, parameters, context): ...

    async def pre_execute(self, context):
        return True

    async def post_execute(self, result, context):
        """可选业务收尾；抛错仍属于业务失败。"""

    async def on_error(self, error, context):
        return JobState.FAILED
