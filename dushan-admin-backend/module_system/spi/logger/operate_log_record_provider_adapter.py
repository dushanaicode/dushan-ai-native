from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_security.bizlog.log_record_entry import LogRecordEntry
from framework.starter_security.bizlog.log_record_operation import LogRecordOperation
from framework.starter_security.public import (
    LogRecordProvider,
    LogRecordReservation,
)
from module_system.service.logger.operate_log_service import OperateLogService


@service(interface=LogRecordProvider)
class OperateLogRecordProviderAdapter(LogRecordProvider):
    delegate: OperateLogService = Inject()

    @override
    async def reserve(self, operation: LogRecordOperation) -> LogRecordReservation:
        return await self.delegate.reserve(operation)

    @override
    async def finalize(self, reservation: LogRecordReservation, entry: LogRecordEntry) -> None:
        return await self.delegate.finalize(reservation, entry)

    @override
    async def renew(self, reservation: LogRecordReservation) -> None:
        return await self.delegate.renew(reservation)

    @override
    async def cancel(self, reservation: LogRecordReservation) -> None:
        return await self.delegate.cancel(reservation)
