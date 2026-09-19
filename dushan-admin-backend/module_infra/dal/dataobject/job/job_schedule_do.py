from datetime import datetime

from sqlalchemy import BigInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.public import (
    GlobalControlDO,
    global_model,
)


@global_model
class JobScheduleDO(GlobalControlDO):
    __tablename__ = "infra_job_schedule"
    __table_args__ = {**GlobalControlDO.__table_args__, "comment": "调度器持久协调记录"}

    job_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, comment="任务编号")
    checkpoint: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="永久定时投递游标；不随历史请求清理"
    )
