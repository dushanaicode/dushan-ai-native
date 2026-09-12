from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from framework.common.utils.id.snowflake_utils import SnowflakeUtils
from framework.starter_database.model.base import Base


class BaseDO(Base):
    """带审计和软删除的单主键实体；时间字段统一保存 UTC naive 值。

    数据库生成 ID 或显式 Snowflake 策略由应用决定；插入/更新由自有 Session
    填充审计值。其他独立 SQLAlchemy Session 不自动获得这些应用策略。
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), Identity(), primary_key=True
    )
    creator: Mapped[str] = mapped_column(String(64), default="")
    create_time: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    updater: Mapped[str] = mapped_column(String(64), default="")
    update_time: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    @staticmethod
    def get_create_time_from_id(identifier: int) -> datetime:
        """仅用于已确定由 Snowflake 策略生成的 ID，非法值明确报错。"""
        return SnowflakeUtils.parse_id(identifier)["datetime"]
