from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass

from server.bootstrap.context import AppBootstrapContext
from server.bootstrap.steps.auth_step import AuthStep
from server.bootstrap.steps.cache_step import CacheStep
from server.bootstrap.steps.captcha_step import CaptchaStep
from server.bootstrap.steps.config_step import bind_server_config
from server.bootstrap.steps.data_permission_step import DataPermissionStep
from server.bootstrap.steps.database_step import DatabaseStep
from server.bootstrap.steps.definitions_step import DefinitionsStep
from server.bootstrap.steps.ip_step import IpStep
from server.bootstrap.steps.job_step import JobStep
from server.bootstrap.steps.logging_step import configure_logging
from server.bootstrap.steps.monitor_step import MonitorStep
from server.bootstrap.steps.mq_step import MQStep
from server.bootstrap.steps.protection_step import ProtectionStep
from server.bootstrap.steps.security_step import SecurityStep
from server.bootstrap.steps.tenant_step import TenantStep
from server.bootstrap.steps.web_step import WebStep
from server.bootstrap.steps.websocket_step import WebSocketStep


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
    BootstrapStepSpec("追踪资源", MonitorStep.run),
    BootstrapStepSpec("地区与 IP 资源", IpStep.run),
    BootstrapStepSpec("缓存资源", CacheStep.run),
    BootstrapStepSpec("第三方授权资源", AuthStep.run),
    BootstrapStepSpec("保护资源", ProtectionStep.run),
    BootstrapStepSpec("验证码资源", CaptchaStep.run),
    BootstrapStepSpec("数据库资源", DatabaseStep.run),
    BootstrapStepSpec("租户隔离", TenantStep.run),
    BootstrapStepSpec("数据权限", DataPermissionStep.run),
    BootstrapStepSpec("本站安全资源", SecurityStep.run),
    BootstrapStepSpec("任务调度", JobStep.run),
    BootstrapStepSpec("消息队列", MQStep.run),
    BootstrapStepSpec("WebSocket 实时连接", WebSocketStep.run),
    BootstrapStepSpec("Web 路由", WebStep.run),
)
