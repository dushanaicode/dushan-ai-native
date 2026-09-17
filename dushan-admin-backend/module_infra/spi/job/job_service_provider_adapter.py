from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_job.spi.job_definition_provider import JobDefinitionProvider
from module_infra.service.job.job_definition_store import JobDefinitionStore


@service(interface=JobDefinitionProvider)
class JobServiceProviderAdapter(JobDefinitionProvider):
    store: JobDefinitionStore = Inject()

    async def list_definitions(self):
        return await self.store.list_definitions()

    async def get_definition(self, job_id):
        return await self.store.get_definition(job_id)

    async def save_definition(self, definition):
        return await self.store.save_definition(definition)

    async def delete_definition(self, job_id):
        return await self.store.delete_definition(job_id)

    async def stop_definition(self, job_id, revision):
        return await self.store.stop_definition(job_id, revision)
