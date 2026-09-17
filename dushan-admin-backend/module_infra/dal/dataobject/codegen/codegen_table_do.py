from sqlalchemy import BigInteger, Boolean, Computed, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from framework.starter_tenant.decorators.tenant_model import global_model
from framework.starter_tenant.entity.global_control_do import GlobalControlDO


@global_model
class CodegenTableDO(GlobalControlDO):
    """代码生成 - 表定义"""

    __tablename__ = "infra_codegen_table"
    __table_args__ = (
        UniqueConstraint(
            "data_source_config_id",
            "table_name",
            "active_key",
            name="uq_infra_codegen_table_active_0",
        ),
        {**GlobalControlDO.__table_args__, **{"comment": "代码生成-表定义"}},
    )

    data_source_config_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="数据源配置编号"
    )
    table_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="表名称")
    table_comment: Mapped[str] = mapped_column(String(500), default="", comment="表描述")
    class_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="实体类名称")
    author: Mapped[str | None] = mapped_column(String(100), comment="作者")
    remark: Mapped[str | None] = mapped_column(String(500), comment="备注")

    # ========== 生成信息 ==========
    template_type: Mapped[int] = mapped_column(
        SmallInteger, default=1, comment="模板类型: 1=CRUD, 2=Tree, 15=主子表"
    )
    front_type: Mapped[int] = mapped_column(SmallInteger, default=0, comment="前端类型")
    scene: Mapped[int] = mapped_column(SmallInteger, default=1, comment="生成场景")
    parent_menu_id: Mapped[int | None] = mapped_column(BigInteger, comment="父菜单编号")
    module_name: Mapped[str] = mapped_column(
        String(100), default="", comment="模块名，如 system、infra"
    )
    business_name: Mapped[str] = mapped_column(
        String(100), default="", comment="业务名，如 user、dict"
    )
    class_comment: Mapped[str] = mapped_column(String(200), default="", comment="类描述，如 用户")

    # ========== 导出配置 ==========
    enable_export: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否启用导出")

    # ========== 树表专用 ==========
    tree_parent_column_id: Mapped[int | None] = mapped_column(BigInteger, comment="树表-父字段编号")
    tree_name_column_id: Mapped[int | None] = mapped_column(BigInteger, comment="树表-名称字段编号")

    # ========== 主子表专用 ==========
    master_table_id: Mapped[int | None] = mapped_column(BigInteger, comment="主子表-主表编号")
    sub_join_column_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="主子表-子表关联字段编号"
    )
    sub_join_many: Mapped[bool | None] = mapped_column(
        Boolean, comment="主子表-关联关系: true=一对多, false=一对一"
    )

    active_key: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed("CASE WHEN deleted = 0 THEN 1 ELSE NULL END"),
        comment="仅有效记录参与业务唯一约束",
    )
