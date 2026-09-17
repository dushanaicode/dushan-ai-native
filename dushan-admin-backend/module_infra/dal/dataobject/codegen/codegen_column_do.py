from sqlalchemy import (
    BigInteger,
    Boolean,
    Computed,
    ForeignKeyConstraint,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.decorators.tenant_model import global_model
from framework.starter_tenant.entity.global_control_do import GlobalControlDO


@global_model
class CodegenColumnDO(GlobalControlDO):
    """代码生成 - 列定义"""

    __tablename__ = "infra_codegen_column"
    __table_args__ = (
        ForeignKeyConstraint(
            ["table_id"], ["infra_codegen_table.id"], name="fk_infra_codegen_column_table_id"
        ),
        UniqueConstraint(
            "table_id", "column_name", "active_key", name="uq_infra_codegen_column_active_0"
        ),
        {**GlobalControlDO.__table_args__, **{"comment": "代码生成-列定义"}},
    )

    table_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="表编号")
    column_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="字段列名")
    column_comment: Mapped[str] = mapped_column(String(500), default="", comment="字段描述")
    data_type: Mapped[str] = mapped_column(String(100), nullable=False, comment="字段物理类型")
    column_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="字段长度")
    field_type: Mapped[str] = mapped_column(String(50), default="str", comment="Python字段类型")
    field_name: Mapped[str] = mapped_column(String(200), default="", comment="Python属性名")

    # ========== CRUD 操作标记 ==========
    create_operation: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="是否参与新增操作"
    )
    update_operation: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="是否参与编辑操作"
    )
    list_operation: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否作为查询条件")
    list_operation_result: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="是否在列表中展示"
    )
    list_operation_condition: Mapped[str] = mapped_column(
        String(20), default="=", comment="查询方式: =, !=, >, >=, <, <=, LIKE, BETWEEN"
    )

    # ========== UI 展示 ==========
    nullable: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否允许为空")
    html_type: Mapped[str] = mapped_column(
        String(50),
        default="input",
        comment="显示类型: input, textarea, select, radio, checkbox, datetime, imageUpload, fileUpload, editor",
    )
    dict_type: Mapped[str | None] = mapped_column(String(200), comment="关联字典类型")
    example: Mapped[str | None] = mapped_column(String(500), comment="示例值")

    # ========== 排序 & 主键 ==========
    order_no: Mapped[int] = mapped_column(SmallInteger, default=0, comment="排序")
    primary_key: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否主键")

    active_key: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed("CASE WHEN deleted = 0 THEN 1 ELSE NULL END"),
        comment="仅有效记录参与业务唯一约束",
    )

    computed_expression: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="数据库生成列表达式"
    )
    computed_persisted: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, comment="生成列是否持久化"
    )
