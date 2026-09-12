from injector import Injector, Provider


class ListBindingProvider(Provider):
    """列表接口复用原绑定，使单例不会因 providers 声明而重复实例化。"""

    def __init__(self, key: type) -> None:
        self._key = key

    def get(self, injector: Injector) -> list[object]:
        return [injector.get(self._key)]
