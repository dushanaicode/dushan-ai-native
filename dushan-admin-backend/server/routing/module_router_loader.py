import importlib
from collections.abc import Sequence

from fastapi import APIRouter

from framework.common.exception.exceptions.configuration_exception import ConfigurationException
from framework.starter_module.core.resolved_module import ResolvedModule
from framework.starter_web.routing.router_registration import RouterRegistration


class ModuleRouterLoader:
    """按启用顺序导入各模块 module.toml 声明的路由；未启用模块不导入、不登记。"""

    @staticmethod
    def registrations(modules: Sequence[ResolvedModule]) -> tuple[RouterRegistration, ...]:
        result = []
        for module in modules:
            for target in module.definition.routers:
                name, _, attribute = target.partition(":")
                package = module.definition.package
                routers = getattr(
                    importlib.import_module(package if name == "." else f"{package}.{name}"),
                    attribute,
                    None,
                )
                if not isinstance(routers, (list, tuple)) or not all(
                    isinstance(router, APIRouter) for router in routers
                ):
                    raise ConfigurationException(
                        msg=f"模块路由声明必须指向 APIRouter 列表: {module.definition.name} ({target})"
                    )
                result.extend(RouterRegistration(router) for router in routers)
        return tuple(result)
