"""汇总应用的配置分组，校验全部已声明字段。"""

from pydantic import BaseModel, ConfigDict, Field

from server.config.granian.granian_settings import GranianSettings
from server.config.server.server_settings import ServerSettings
from server.config.uvicorn.uvicorn_settings import UvicornSettings


class ApplicationSettings(BaseModel):
    """YAML 的分组对应各自的强类型配置模型。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    server: ServerSettings
    granian: GranianSettings = Field(default_factory=GranianSettings)
    uvicorn: UvicornSettings = Field(default_factory=UvicornSettings)
