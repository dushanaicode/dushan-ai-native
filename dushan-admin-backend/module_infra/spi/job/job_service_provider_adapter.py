from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_job.public import (
    JobDefinition,
    JobDefinitionProvider,
)
from module_infra.service.job.job_definition_service import JobDefinitionService


@service(interface=JobDefinitionProvider)
class JobServiceProviderAdapter(JobDefinitionProvider):
    store: JobDefinitionService = Inject()

    @override
    async def list_definitions(self) -> tuple[JobDefinition, ...]:
        return await self.store.list_definitions()

    @override
    async def get_definition(self, job_id: str) -> JobDefinition | None:
        return await self.store.get_definition(job_id)

    @override
    async def save_definition(self, definition: JobDefinition) -> None:
        return await self.store.save_definition(definition)

    @override
    async def delete_definition(self, job_id: str) -> None:
        return await self.store.delete_definition(job_id)

    @override
    async def stop_definition(self, job_id: str, revision: str) -> None:
        return await self.store.stop_definition(job_id, revision)
