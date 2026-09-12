from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass

from server.bootstrap.context import AppBootstrapContext
from server.bootstrap.steps.config_step import bind_server_config
from server.bootstrap.steps.definitions_step import DefinitionsStep
from server.bootstrap.steps.logging_step import configure_logging


@dataclass(frozen=True, slots=True)
class BootstrapStepSpec:
    """记录启动步骤的名称，以及负责启动和清理的处理函数。"""

    name: str
    handler: Callable[[AppBootstrapContext], AbstractAsyncContextManager[None]]
    requires_di: bool = False


APP_BOOTSTRAP_STEPS = (
    BootstrapStepSpec("配置绑定", bind_server_config),
    BootstrapStepSpec("Loguru 日志", configure_logging),
    BootstrapStepSpec("模块定义与国际化", DefinitionsStep.run),
)
