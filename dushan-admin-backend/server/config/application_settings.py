from pydantic import BaseModel, ConfigDict

from framework.common.datetime.core.datetime_options import DateTimeOptions
from framework.common.i18n.core.i18n_options import I18nOptions
from framework.common.page.config.page_settings import PageSettings
from framework.common.response.config.response_settings import ResponseSettings
from framework.common.utils.el.expression_options import ExpressionOptions
from framework.starter_config.config.config_settings import ConfigSettings
from framework.starter_di.config.di_settings import DiSettings
from framework.starter_logging.config.log_settings import LogSettings
from framework.starter_module.config.module_settings import ModuleSettings
from framework.starter_scanner.config.scanner_config import ScannerConfig
from framework.starter_web.config.banner_settings import BannerSettings
from server.config.granian.granian_settings import GranianSettings
from server.config.server.server_settings import ServerSettings
from server.config.uvicorn.uvicorn_settings import UvicornSettings


class ApplicationSettings(BaseModel):
    """组合服务、公共组件、日志和两个 HTTP 引擎的完整配置。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    server: ServerSettings
    log: LogSettings
    granian: GranianSettings
    uvicorn: UvicornSettings
    i18n: I18nOptions
    page: PageSettings
    response: ResponseSettings
    datetime: DateTimeOptions
    expression: ExpressionOptions
    banner: BannerSettings
    modules: ModuleSettings
    scanner: ScannerConfig
    config: ConfigSettings
    di: DiSettings
