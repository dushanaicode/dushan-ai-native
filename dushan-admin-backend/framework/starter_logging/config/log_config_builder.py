from pathlib import Path

from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_logging.config.log_settings import LogSettings


class LogConfigBuilder:
    """server 启动期日志配置构建器。"""

    @staticmethod
    def get_config(*, base_dir: str | Path, app_env: str | None = None) -> LogSettings:
        """通过实例化配置提供者读取 log 分组，沿用 YAML 和环境变量优先级。"""
        provider = BootstrapConfigProvider.load(base_dir, app_env=app_env)
        return provider.get_config(LogSettings, prefix="LOG_")
