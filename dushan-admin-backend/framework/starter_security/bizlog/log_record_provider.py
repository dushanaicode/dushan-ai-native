from typing import Protocol

from framework.starter_security.bizlog.log_record_entry import LogRecordEntry
from framework.starter_security.bizlog.log_record_operation import LogRecordOperation
from framework.starter_security.bizlog.log_record_reservation import LogRecordReservation


class LogRecordProvider(Protocol):
    """业务持久审计接点，连接、事务、outbox 及故障恢复归业务提供者。

    reserve 在业务前执行，失败会阻止业务开始；finalize/cancel/renew 的失败
    单独报告，不能把已提交的业务成功伪装为回滚。事务内写入必须用现有
    Database 提交后动作或业务 outbox，不由 Security 新建事务管理器。
    提供者不能再次调用自身的审计装饰器。
    """

    async def reserve(self, operation: LogRecordOperation) -> LogRecordReservation: ...

    async def finalize(self, reservation: LogRecordReservation, entry: LogRecordEntry) -> None: ...

    async def renew(self, reservation: LogRecordReservation) -> None: ...

    async def cancel(self, reservation: LogRecordReservation) -> None: ...
