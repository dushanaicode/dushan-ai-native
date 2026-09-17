from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.decorators.tenant_model import global_model
from framework.starter_tenant.entity.global_control_do import GlobalControlDO


@global_model
class JobLogDO(GlobalControlDO):
    __tablename__ = "infra_job_log"
    __table_args__ = ({**GlobalControlDO.__table_args__, **{"comment": "定时任务的执行日志"}},)

    job_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="任务编号，关联 JobDO.id"
    )
    handler_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="处理器的名字，冗余字段 JobDO.handler_name"
    )
    handler_param: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="处理器的参数，冗余字段 JobDO.handler_param"
    )
    execute_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="第几次执行，用于区分是不是重试执行。如果是重试执行，则 index 大于 1",
    )
    begin_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="开始执行时间"
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="结束执行时间"
    )
    duration: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="执行时长，单位：毫秒"
    )
    status: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="状态，枚举 【JobLogStatusEnum】"
    )
    result: Mapped[str | None] = mapped_column(
        String(4096), nullable=True, comment="结果数据，成功时是执行结果，失败时是异常堆栈"
    )
    request_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True, comment="持久执行请求编号"
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False, comment="Native 执行终态")
