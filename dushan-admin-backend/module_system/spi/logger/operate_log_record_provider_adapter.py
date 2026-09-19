from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_security.public import (
    LogRecordProvider,
)
from module_system.service.logger.operate_log_service import OperateLogService


@service(interface=LogRecordProvider)
class OperateLogRecordProviderAdapter(LogRecordProvider):
    delegate: OperateLogService = Inject()

    async def reserve(self, operation):
        return await self.delegate.reserve(operation)

    async def finalize(self, reservation, entry):
        return await self.delegate.finalize(reservation, entry)

    async def renew(self, reservation):
        return await self.delegate.renew(reservation)

    async def cancel(self, reservation):
        return await self.delegate.cancel(reservation)
