from sqlalchemy import (
    BigInteger,
    Computed,
    ForeignKeyConstraint,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.public import (
    TenantBaseDO,
)


class InfraConfigDataDO(TenantBaseDO):
    __tablename__ = "infra_config_data"
    __table_args__ = (
        Index("ix_infra_config_data_tenant", "tenant_id"),
        ForeignKeyConstraint(
            ["tenant_id", "type_id"],
            ["infra_config_type.tenant_id", "infra_config_type.id"],
            name="fk_infra_config_data_type_id",
        ),
        UniqueConstraint("tenant_id", "key", "active_key", name="uq_infra_config_data_active_0"),
        {**TenantBaseDO.__table_args__, **{"comment": "参数配置表"}},
    )

    type_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="配置类型ID")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="参数名称")
    key: Mapped[str] = mapped_column(String(100), nullable=False, comment="参数键名")
    value: Mapped[str] = mapped_column(String(500), nullable=False, comment="参数键值")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="配置描述")
    input_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="UI控件类型")
    input_props: Mapped[str | None] = mapped_column(Text, nullable=True, comment="UI控件属性JSON")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="显示顺序")
    visible: Mapped[bool] = mapped_column(Integer, default=False, comment="是否可见")
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="备注")

    active_key: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed("CASE WHEN deleted = 0 THEN 1 ELSE NULL END"),
        comment="仅有效记录参与业务唯一约束",
    )
