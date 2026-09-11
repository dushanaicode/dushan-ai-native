from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import FastAPI
from loguru import logger as loguru_logger

from framework.common.datetime.core.date_utils import DateUtils
from framework.common.exception.core.exception_handler import GlobalExceptionHandler
from framework.common.i18n.core.i18n_options import I18nOptions
from framework.common.page.config.page_settings import PageSettings
from framework.common.response.config.response_settings import ResponseSettings
from framework.common.response.core.middleware_result import MiddlewareResult
from framework.common.utils.el.expression_utils import ExpressionUtils
from framework.starter_logging.config.log_settings import LogSettings
from framework.starter_logging.starter.logging_starter import LoggingStarter
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
    ready: bool = False
    logging_owner: str = field(default_factory=lambda: uuid4().hex)
    logger: "Logger" = field(init=False)
    logging_starter: LoggingStarter | None = None

    def __post_init__(self) -> None:
        """给当前应用绑定日志归属，受管 sink 据此隔离输出。"""
        self.logger = loguru_logger.bind(logging_owner=self.logging_owner)
