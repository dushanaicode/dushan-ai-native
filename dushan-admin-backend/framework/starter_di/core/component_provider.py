from typing import TYPE_CHECKING

from injector import Injector, Provider

from framework.starter_di.core.component_binding import ComponentBinding

if TYPE_CHECKING:
    from framework.starter_di.core.di_container import DiContainer


class ComponentProvider(Provider):
    """把原生 Injector 的实例创建交给当前应用的生命周期入口。"""

    def __init__(self, container: "DiContainer", binding: ComponentBinding) -> None:
        self._container = container
        self._binding = binding

    def get(self, injector: Injector) -> object:
        return self._container.create_component(self._binding)
