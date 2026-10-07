from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Computed,
    DateTime,
    Identity,
    Integer,
    String,
    and_,
    case,
    column,
    false,
    null,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import ColumnElement

from framework.starter_database.id.snowflake_utils import SnowflakeUtils
from framework.starter_database.model.base import Base


class BaseDO(Base):
    """带审计和软删除的单主键实体；时间字段统一保存 UTC naive 值。

    数据库生成 ID 或显式 Snowflake 策略由应用决定；插入/更新由自有 Session
    填充审计值。其他独立 SQLAlchemy Session 不自动获得这些应用策略。
    """

    __abstract__ = True
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
    }

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        Identity(),
        primary_key=True,
        comment="主键 ID",
    )
    creator: Mapped[str] = mapped_column(String(64), default="", comment="创建者账号 ID")
    create_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), comment="创建时间（UTC）"
    )
    updater: Mapped[str] = mapped_column(String(64), default="", comment="更新者账号 ID")
    update_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), comment="更新时间（UTC）"
    )
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已删除")

    @staticmethod
    def active_key_computed(*conditions: ColumnElement[bool]) -> Computed:
        """为未删除且满足附加条件的记录生成唯一标记，布尔值由目标方言编译。"""
        return Computed(
            case((and_(column("deleted", Boolean) == false(), *conditions), 1), else_=null())
        )

    @staticmethod
    def get_create_time_from_id(identifier: int) -> datetime:
        """返回Snowflake ID对应的UTC aware时间，与本实体存储的UTC naive字段区分。"""
        return SnowflakeUtils.parse_id(identifier)["datetime"]
