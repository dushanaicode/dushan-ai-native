from sqlalchemy import Boolean, Computed, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.public import (
    GlobalControlDO,
    global_model,
)


@global_model
class MqDO(GlobalControlDO):
    __tablename__ = "infra_mq"
    __table_args__ = (
        UniqueConstraint("consumer", "active_key", name="uq_infra_mq_active_0"),
        {**GlobalControlDO.__table_args__, **{"comment": "MQ 消息的定义"}},
    )

    topic: Mapped[str] = mapped_column(String(255), nullable=False, comment="消息主题 Topic")
    consumer: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="消费者名称，即处理函数名"
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=3, comment="重试次数")
    description: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="描述")

    active_key: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed("CASE WHEN deleted = 0 THEN 1 ELSE NULL END"),
        comment="仅有效记录参与业务唯一约束",
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="部署覆盖开关"
    )
    concurrency: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="部署覆盖并发数"
    )
    prefetch: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="部署覆盖预取数")
