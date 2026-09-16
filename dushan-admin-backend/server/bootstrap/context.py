from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import FastAPI
from loguru import logger as loguru_logger

from framework.common.datetime.core.date_utils import DateUtils
from framework.common.page.config.page_settings import PageSettings
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_di.config.di_settings import DiSettings
from framework.starter_i18n.core.i18n_options import I18nOptions
from framework.starter_logging.config.log_settings import LogSettings
from framework.starter_logging.starter.logging_starter import LoggingStarter
from framework.starter_module.config.module_settings import ModuleSettings
from framework.starter_scanner.config.scanner_config import ScannerConfig
from framework.starter_security.bizlog.expression.expression_utils import ExpressionUtils
from framework.starter_web.config.banner_settings import BannerSettings
from framework.starter_web.config.response_settings import ResponseSettings
from framework.starter_web.exception.exception_handler import GlobalExceptionHandler
from framework.starter_web.response.middleware_result import MiddlewareResult
from server.bootstrap.application_definitions import ApplicationDefinitions
from server.config.server.server_settings import ServerSettings

if TYPE_CHECKING:
    from loguru import Logger


@dataclass(slots=True)
class AppBootstrapContext:
    """保存当前应用的配置、日志、异常处理器和启动状态。"""

    app: FastAPI
    base_dir: Path
    settings: ServerSettings
    config_sources: Mapping[str, str]
    log_settings: LogSettings
    i18n_options: I18nOptions
    page_settings: PageSettings
    response_settings: ResponseSettings
    exception_handler: GlobalExceptionHandler
    middleware_result: MiddlewareResult
    date_utils: DateUtils
    expression_utils: ExpressionUtils
    banner_settings: BannerSettings
    module_settings: ModuleSettings
    scanner_config: ScannerConfig
    bootstrap_config: BootstrapConfigProvider
    di_settings: DiSettings
    definitions: ApplicationDefinitions | None = None
    ready: bool = False
    logging_owner: str = field(default_factory=lambda: uuid4().hex)
    logger: "Logger" = field(init=False)
    logging_starter: LoggingStarter | None = None
    before_drain: list[Callable[[], Awaitable[None]]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """给当前应用绑定日志归属，受管 sink 据此隔离输出。"""
        self.logger = loguru_logger.bind(logging_owner=self.logging_owner)
