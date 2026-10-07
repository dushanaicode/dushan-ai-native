from typing import Protocol, runtime_checkable

from framework.starter_job.public import JobDefinition


@runtime_checkable
class JobDefinitionService(Protocol):
    """读写调度运行时使用的任务定义。"""

    async def list_definitions(self) -> tuple[JobDefinition, ...]: ...

    async def get_definition(self, job_id: str) -> JobDefinition | None: ...

    async def save_definition(self, definition: JobDefinition) -> None: ...

    async def delete_definition(self, job_id: str) -> None: ...

    async def stop_definition(self, job_id: str, revision: str) -> None: ...
