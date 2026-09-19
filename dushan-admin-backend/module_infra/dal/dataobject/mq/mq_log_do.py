from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.public import (
    GlobalControlDO,
    global_model,
)


@global_model
class MqLogDO(GlobalControlDO):
    __tablename__ = "infra_mq_log"
    __table_args__ = ({**GlobalControlDO.__table_args__, **{"comment": "MQ 消息的消费日志"}},)

    message_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="消息ID"
    )
    topic: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="消息主题")
    consumer: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="消费者名称，冗余字段"
    )
    execute_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="第几次消费，用于区分是不是重试消费。如果是重试，则 index 大于 1",
    )
    begin_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="开始消费时间"
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="结束消费时间"
    )
    duration: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="消费时长，单位：毫秒"
    )
    status: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="状态，枚举 MqLogStatusEnum"
    )
    result: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="结果数据，成功时是执行结果，失败时是异常堆栈"
    )
    payload: Mapped[Any | None] = mapped_column(
        JSON, nullable=True, comment="仅留空字段承接历史表结构；不记录正文或身份凭证"
    )

    state: Mapped[str] = mapped_column(String(32), nullable=False, comment="Native 消费终态")
