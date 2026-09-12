from pydantic import Field

from framework.starter_config.config.config_model import ConfigModel


class DatabasePoolSettings(ConfigModel):
    """连接池容量与等待时间；默认值由应用 YAML 提供。"""

    size: int = Field(ge=1)
    max_overflow: int = Field(ge=0)
    timeout_seconds: float = Field(gt=0)
    recycle_seconds: int = Field(ge=-1)
    pre_ping: bool
