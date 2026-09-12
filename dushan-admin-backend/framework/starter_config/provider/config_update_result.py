from dataclasses import dataclass

from framework.starter_config.provider.config_change import ConfigChange


@dataclass(frozen=True, slots=True)
class ConfigUpdateResult:
    """配置提交结果；通知失败可见，但不会伪称已提交的配置被回滚。"""

    change: ConfigChange
    listener_errors: tuple[BaseException, ...]
