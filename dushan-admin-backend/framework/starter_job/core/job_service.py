from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.decorators.components import framework
from framework.starter_di.definitions.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_job.definitions.constants.job_error_codes import JobErrorCodes
from framework.starter_job.exception.job_exception import JobException


@framework(scope=ComponentScopeEnum.SINGLETON)
class JobService:
    """业务端提交/修改计划；提交后只通知或同步副本，不执行任务。"""

    def __init__(self, database: SessionProvider):
        self.database = database
        self.runtime = None

    def _runtime(self):
        if self.runtime is None or not self.runtime.accepting:
            raise JobException(JobErrorCodes.CLOSED)
        return self.runtime

    async def trigger(self, job_id):
        return await self._runtime().submit_manual(job_id)

    async def save(self, definition):
        runtime = self._runtime()
        runtime.registry.validate(definition)
        async with self.database.transaction():
            await runtime.definitions.save_definition(definition)
            self.database.after_commit(
                self.synchronize, required=True, name="job-definition-changed"
            )

    async def delete(self, job_id):
        runtime = self._runtime()
        async with self.database.transaction():
            await runtime.definitions.delete_definition(job_id)
            self.database.after_commit(
                self.synchronize, required=True, name="job-definition-deleted"
            )

    async def synchronize(self):
        runtime = self._runtime()
        await runtime.requests.notify_changed()
        if runtime.owner:
            await runtime.reconcile()

    def preview(self, definition, after, count):
        return self._runtime().registry.validate(definition).preview(after, count)
