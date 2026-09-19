from collections.abc import Callable, Mapping
from typing import TypeVar

from pydantic import BaseModel

from framework.common.component.component_metadata import ComponentMetadata
from framework.common.enums.component_type_enum import ComponentTypeEnum
from framework.starter_config.decorator.config_model_metadata import ConfigModelMetadata
from framework.starter_config.definitions.enums.config_source_enum import ConfigSourceEnum

T = TypeVar("T", bound=type[BaseModel])


def config_model(
    name: str,
    *,
    env_prefix: str,
    sources: tuple[ConfigSourceEnum, ...] | None = None,
    field_sources: Mapping[str, tuple[ConfigSourceEnum, ...]] | None = None,
    field_keys: Mapping[str, str] | None = None,
) -> Callable[[T], T]:
    """声明 config.models.<name> 的模型；无运行实例或全局注册副作用。"""
    metadata = ConfigModelMetadata(
        name,
        env_prefix,
        sources,
        {} if field_sources is None else field_sources,
        {} if field_keys is None else field_keys,
    )

    def mark(model: T) -> T:
        if not isinstance(model, type) or not issubclass(model, BaseModel):
            raise TypeError("config_model 只能标记 Pydantic 模型类")
        ComponentMetadata(ComponentTypeEnum.CONFIG_MODEL).attach(model)
        setattr(model, ConfigModelMetadata.ATTRIBUTE, metadata)
        return model

    return mark
