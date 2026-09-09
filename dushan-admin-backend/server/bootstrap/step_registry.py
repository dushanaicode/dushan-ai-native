"""本轮实际可用的启动步骤。"""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass

from server.bootstrap.context import AppBootstrapContext
from server.bootstrap.steps.config_step import bind_server_config
from server.bootstrap.steps.logging_step import configure_logging


@dataclass(frozen=True, slots=True)
class BootstrapStepSpec:
    """每个步骤用异步上下文同时表达启动与清理。"""

    name: str
    handler: Callable[[AppBootstrapContext], AbstractAsyncContextManager[None]]


APP_BOOTSTRAP_STEPS = (
    BootstrapStepSpec("配置绑定", bind_server_config),
    BootstrapStepSpec("控制台日志", configure_logging),
)
