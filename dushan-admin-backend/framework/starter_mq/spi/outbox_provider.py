from datetime import datetime
from typing import Protocol

from framework.starter_mq.definitions.enums.outbox_state import OutboxState
from framework.starter_mq.model.outbox_record import OutboxRecord
from framework.starter_mq.model.publish_receipt import PublishReceipt


class OutboxProvider(Protocol):
    """业务模块持久 outbox，不在框架启动时建表。

    insert 加入调用者的同一受管事务；记录内容不可修改，同 ID 内容冲突必须拒绝。
    claim 在独立短事务中锁定当前 PENDING 且到期行，原子增加 attempts 并转 SENDING，
    返回持久随机 token/期限。达到上限转 DEAD；过期 SENDING 转 UNKNOWN，不盲目重发。
    finish 必须 CAS token、SENDING 和未过期租约；同一成功回执重试应幂等。
    到期与租约时间必须保留微秒精度，不能因数据库默认舍入而改变立即发布或认领边界。
    取消只允许 PENDING→CANCELLED；清理只删除保留期外 PUBLISHED/DEAD/CANCELLED，
    UNKNOWN 必须经业务人工核定后才能转终态。查询/写入必须执行声明的租户或全局规则。
    """

    async def insert(self, record: OutboxRecord) -> None: ...

    async def claim(
        self, *, now: datetime, lease_seconds: float, max_attempts: int, record_id: str | None
    ) -> OutboxRecord | None: ...

    async def finish(
        self,
        record: OutboxRecord,
        *,
        state: OutboxState,
        ready_at: datetime,
        error_type: str | None,
        receipt: PublishReceipt | None,
    ) -> None: ...

    async def cancel(self, record_id: str) -> bool: ...

    async def cleanup(self, *, before: datetime, limit: int) -> int: ...
