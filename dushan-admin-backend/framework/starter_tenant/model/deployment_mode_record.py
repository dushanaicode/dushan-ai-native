from sqlalchemy import Boolean, MetaData, String
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.enums.tenant_model_kind import TenantModelKind
from framework.starter_tenant.model.global_control_do import GlobalControlDO


class DeploymentModeRecord(GlobalControlDO):
    """只由启动封存和独立部署作业访问的全局单例，不属于业务租户目录。"""

    __tablename__ = "framework_tenant_deployment"
    __tenant_kind__ = TenantModelKind.GLOBAL
    metadata = MetaData()
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    default_tenant_id: Mapped[str] = mapped_column(String(256), nullable=False)
    profile: Mapped[str] = mapped_column(String(32), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
