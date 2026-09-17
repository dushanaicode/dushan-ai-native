from sqlalchemy import (
    BigInteger,
    Computed,
    ForeignKeyConstraint,
    Index,
    LargeBinary,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import LONGBLOB
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.entity.tenant_base_do import TenantBaseDO


class FileContentDO(TenantBaseDO):
    __tablename__ = "infra_file_content"
    __table_args__ = (
        Index("ix_infra_file_content_tenant", "tenant_id"),
        ForeignKeyConstraint(
            ["tenant_id", "config_id"],
            ["infra_file_config.tenant_id", "infra_file_config.id"],
            name="fk_infra_file_content_config_id",
        ),
        UniqueConstraint(
            "tenant_id", "config_id", "path", "active_key", name="uq_infra_file_content_active_0"
        ),
        {**TenantBaseDO.__table_args__, **{"comment": "文件内容表"}},
    )

    config_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="配置编号")
    path: Mapped[str] = mapped_column(String(255), nullable=False, comment="路径，即文件名")
    content: Mapped[bytes] = mapped_column(
        LargeBinary().with_variant(LONGBLOB(), "mysql"), nullable=False, comment="文件内容"
    )

    active_key: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed("CASE WHEN deleted = 0 THEN 1 ELSE NULL END"),
        comment="仅有效记录参与业务唯一约束",
    )
