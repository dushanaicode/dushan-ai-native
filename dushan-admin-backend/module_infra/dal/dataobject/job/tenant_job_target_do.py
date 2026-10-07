from sqlalchemy import BigInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.public import GlobalControlDO, global_model


@global_model
class TenantJobTargetDO(GlobalControlDO):
    __tablename__ = "infra_tenant_job_target"
    __table_args__ = (
        UniqueConstraint("request_id", "tenant_id", name="uq_infra_tenant_job_target"),
        {**GlobalControlDO.__table_args__, "comment": "定时任务逐租户执行与认领记录"},
    )

    request_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="调度请求编号")
    tenant_id: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="执行目标租户；控制面记录不参与租户行过滤"
    )
    state: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="pending/claimed/completed/unknown"
    )
    token: Mapped[str] = mapped_column(String(32), nullable=False, comment="本次认领凭证")
    expires_at_us: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="认领到期 UTC Unix 微秒，跨数据库保持精度"
    )
