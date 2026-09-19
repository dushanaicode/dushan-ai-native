from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.public import (
    GlobalControlDO,
    global_model,
)


@global_model
class JobRequestDO(GlobalControlDO):
    __tablename__ = "infra_job_request"
    __table_args__ = {**GlobalControlDO.__table_args__, "comment": "调度器持久协调记录"}

    request_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, comment="跨进程幂等请求编号"
    )
    job_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="任务编号")
    request: Mapped[dict] = mapped_column(JSON, nullable=False, comment="Native JobRequest 快照")
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True, comment="pending/claimed/执行终态"
    )
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="独占调度 owner")
    ready_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True, comment="允许领取时间 UTC"
    )
