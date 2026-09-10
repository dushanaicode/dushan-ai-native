from pydantic import BaseModel, ConfigDict, Field

from framework.common.i18n.core.i18n_options import I18nOptions
from framework.starter_logging.config.log_settings import LogSettings
from server.config.granian.granian_settings import GranianSettings
from server.config.server.server_settings import ServerSettings
from server.config.uvicorn.uvicorn_settings import UvicornSettings


class ApplicationSettings(BaseModel):
    """组合服务、日志、国际化和两个 HTTP 引擎的完整配置。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    server: ServerSettings
    log: LogSettings = Field(default_factory=LogSettings)
    granian: GranianSettings = Field(default_factory=GranianSettings)
    uvicorn: UvicornSettings = Field(default_factory=UvicornSettings)
    i18n: I18nOptions = Field(default_factory=I18nOptions)
