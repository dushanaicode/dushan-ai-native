from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.decorators.tenant_model import global_model
from framework.starter_tenant.entity.global_control_do import GlobalControlDO


@global_model
class JobSignalDO(GlobalControlDO):
    __tablename__ = "infra_job_signal"
    __table_args__ = {**GlobalControlDO.__table_args__, "comment": "调度器持久协调记录"}

    revision: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, comment="任务定义提交后的合并通知版本"
    )
