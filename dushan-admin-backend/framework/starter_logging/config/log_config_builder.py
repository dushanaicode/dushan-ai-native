from pathlib import Path

from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_logging.config.log_settings import LogSettings


class LogConfigBuilder:
    """server 启动期日志配置构建器。"""

    @staticmethod
    def get_config(*, base_dir: str | None = None, app_env: str | None = None) -> LogSettings:
        """通过实例化配置提供者读取 log 分组，沿用 YAML 和环境变量优先级。"""
        root = Path(base_dir) if base_dir is not None else Path(__file__).resolve().parents[3]
        provider = BootstrapConfigProvider.load(root, app_env=app_env)
        return provider.get_config(LogSettings, prefix="LOG_")
