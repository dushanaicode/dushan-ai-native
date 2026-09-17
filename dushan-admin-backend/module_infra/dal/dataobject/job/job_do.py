from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Computed,
    DateTime,
    Float,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.decorators.tenant_model import global_model
from framework.starter_tenant.entity.global_control_do import GlobalControlDO


@global_model
class JobDO(GlobalControlDO):
    __tablename__ = "infra_job"
    __table_args__ = (
        UniqueConstraint("handler_name", "active_key", name="uq_infra_job_active_0"),
        {**GlobalControlDO.__table_args__, **{"comment": "定时任务 DO"}},
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="任务名称")
    status: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="任务状态，枚举 【JobStatusEnum】"
    )
    handler_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="处理器的名字")
    handler_param: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="处理器的参数"
    )
    cron_expression: Mapped[str] = mapped_column(String(255), nullable=False, comment="CRON 表达式")
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="重试次数，如果不重试，则设置为 0"
    )
    retry_interval: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="重试间隔，单位：毫秒，如果没有间隔，则设置为 0"
    )
    monitor_timeout: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="监控超时时间，单位：毫秒，为空时，表示不监控"
    )

    active_key: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed("CASE WHEN deleted = 0 THEN 1 ELSE NULL END"),
        comment="仅有效记录参与业务唯一约束",
    )

    revision: Mapped[str] = mapped_column(String(64), nullable=False, comment="计划版本")
    effective_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="版本生效时间 UTC"
    )
    parameters: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, comment="经过 handler 参数模型验证的值"
    )
    tenant_id: Mapped[str | None] = mapped_column(
        String(256), nullable=True, comment="任务目标租户；控制面记录不参与行租户过滤"
    )
    fan_out: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否向已授权租户扇出"
    )
    max_instances: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="最大并发数"
    )
    timeout_seconds: Mapped[float] = mapped_column(
        Float, nullable=False, default=300, comment="单次执行上限"
    )
    retry_backoff: Mapped[float] = mapped_column(
        Float, nullable=False, default=1, comment="重试退避倍率"
    )
    stop_after_failure: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="失败后停止匹配版本"
    )
