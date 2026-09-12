from injector import Injector, Provider
from pydantic import BaseModel

from framework.starter_config.provider.config_provider import ConfigProvider


class ConfigModelProvider(Provider):
    """配置生命周期归 ConfigProvider，DI 只读取其最新有效模型副本。"""

    def __init__(self, configuration: ConfigProvider, model: type[BaseModel]) -> None:
        self._configuration = configuration
        self._model = model

    def get(self, injector: Injector) -> BaseModel:
        return self._configuration.get_config(self._model)
