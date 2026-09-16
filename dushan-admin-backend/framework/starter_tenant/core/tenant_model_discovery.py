from sqlalchemy.orm.mapper import _all_registries


class TenantModelDiscovery:
    """检查已启用包的全部已映射类，包括忘记扫描装饰器的模型。

    只读取 SQLAlchemy 当前映射快照，不安装全局事件、不保存其他应用的模型。
    注册表内部入口与已锁定 SQLAlchemy 版本一并验证。
    """

    @staticmethod
    def collect(packages, components):
        models = {model for model in components if "__table__" in vars(model)}
        for registry in _all_registries():
            for mapper in tuple(registry.mappers):
                model = mapper.class_
                if any(
                    model.__module__ == package or model.__module__.startswith(package + ".")
                    for package in packages
                ):
                    models.add(model)
        return tuple(sorted(models, key=lambda model: (model.__module__, model.__qualname__)))
