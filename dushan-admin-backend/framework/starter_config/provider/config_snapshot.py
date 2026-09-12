from collections.abc import Mapping
from typing import TypeVar

from pydantic import BaseModel

from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError

T = TypeVar("T", bound=BaseModel)


class ConfigSnapshot:
    """固定版本的只读配置视图；每次读取返回副本，不提供修改或刷新入口。"""

    def __init__(
        self,
        models: Mapping[type[BaseModel], BaseModel],
        sources: Mapping[type[BaseModel], Mapping[str, str]],
        revision: int,
    ) -> None:
        self._models = {model: value.model_copy(deep=True) for model, value in models.items()}
        self._sources = {model: dict(value) for model, value in sources.items()}
        self._revision = revision

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def model_classes(self) -> tuple[type[BaseModel], ...]:
        return tuple(self._models)

    def read(self, model: type[T]) -> tuple[T, dict[str, str], int]:
        if model not in self._models:
            raise BootstrapConfigError(f"配置模型未注册：{model.__module__}.{model.__qualname__}")
        return self._models[model].model_copy(deep=True), dict(self._sources[model]), self._revision

    def get_config(self, model: type[T]) -> T:
        return self.read(model)[0]

    def get_sources(self, model: type[BaseModel]) -> dict[str, str]:
        return self.read(model)[1]
