from typing import Literal

from pydantic import Field, SecretStr, field_validator
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from framework.starter_config.config.config_model import ConfigModel
from framework.starter_database.config.database_pool_settings import DatabasePoolSettings
from framework.starter_database.config.database_tls_settings import DatabaseTlsSettings


class DataSourceSettings(ConfigModel):
    """一个具名端点；pool=null 明确继承应用连接池配置。"""

    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,62}$")
    url: SecretStr
    role: Literal["primary", "replica", "named"]
    weight: int = Field(ge=1, le=1000)
    pool: DatabasePoolSettings | None
    tls: DatabaseTlsSettings | None

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: SecretStr) -> SecretStr:
        """只解析结构；加载驱动和真实连接留到启动阶段。"""
        try:
            url = make_url(value.get_secret_value())
        except ArgumentError:
            raise ValueError("数据库 URL 格式无效") from None
        if "+" not in url.drivername:
            raise ValueError("数据库 URL 必须显式指定异步驱动")
        return value
