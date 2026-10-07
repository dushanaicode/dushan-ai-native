from sqlalchemy import BigInteger, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.public import TenantBaseDO


class MqOutboxDO(TenantBaseDO):
    """租户可靠发布记录；签名原文不可变，调度时间使用 UTC 微秒整数。"""

    __tablename__ = "infra_mq_outbox"
    __table_args__ = (
        UniqueConstraint("tenant_id", "record_id", name="uk_mq_outbox_tenant_record"),
        Index("idx_mq_outbox_ready", "tenant_id", "state", "ready_at_us"),
        Index("idx_mq_outbox_lease", "tenant_id", "state", "claim_expires_at_us"),
        {**TenantBaseDO.__table_args__, "comment": "租户 MQ 可靠发布记录"},
    )

    record_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="入箱幂等编号")
    message: Mapped[str] = mapped_column(
        Text().with_variant(LONGTEXT(), "mysql"),
        nullable=False,
        comment="PreparedMessage 原始 JSON 文本",
    )
    state: Mapped[str] = mapped_column(String(16), nullable=False, comment="可靠发布状态")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, comment="已认领次数")
    created_at_us: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="入箱时间 UTC 微秒"
    )
    ready_at_us: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="允许发布时间 UTC 微秒"
    )
    claim_token: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="当前认领令牌"
    )
    claim_expires_at_us: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="租约截止 UTC 微秒"
    )
    finished_at_us: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="结算时间 UTC 微秒"
    )
    error_type: Mapped[str | None] = mapped_column(Text, nullable=True, comment="失败异常类型")
    settled_token: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="已结算认领令牌"
    )
    receipt: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Broker 确认回执 JSON")
