from contextlib import asynccontextmanager

from framework.common.enums.component_type_enum import ComponentTypeEnum
from framework.starter_di.core.candidate_selection import CandidateSelection
from framework.starter_di.enums.binding_outcome_enum import BindingOutcomeEnum
from framework.starter_ip.config.ip_settings import IpSettings
from framework.starter_web.routing.controller_metadata import ControllerMetadata
from server.bootstrap.context import AppBootstrapContext


class WebStep:
    """定义与资源装配后发布活动控制器；关闭只移除本步骤创建的路由。"""

    @staticmethod
    @asynccontextmanager
    async def run(ctx: AppBootstrapContext):
        definitions = ctx.definitions
        controllers = [
            cls
            for cls in definitions.scan_result.get_components(
                component_type=ComponentTypeEnum.COMPONENT
            )
            if ControllerMetadata.ATTRIBUTE in vars(cls)
        ]
        application = definitions.application_context
        if controllers and application is None:
            raise ValueError("注册控制器要求启用 DI")
        selected = (
            set()
            if application is None
            else {
                item.component
                for item in application.container.get_binding_diagnostics()
                if item.outcome is BindingOutcomeEnum.SELECTED
            }
        )
        before = {id(route) for route in ctx.app.routes}
        created = set()
        if IpSettings in definitions.configuration.model_classes:
            ctx.app.state.web_trusted_proxies = definitions.configuration.get_config(
                IpSettings
            ).trusted_proxy_cidrs
        try:
            ctx.app.state.web_routes.register_controllers(
                cls for cls in controllers if CandidateSelection.qualified_name(cls) in selected
            )
            created = {id(route) for route in ctx.app.routes if id(route) not in before}
            ctx.app.state.web_routes.seal()
            yield
        finally:
            ctx.app.state.web_routes.unseal()
            ctx.app.state.web_trusted_proxies = ()
            # 即使审计失败也撤销本次发布，其他已存在的宿主路由继续保留。
            ctx.app.router.routes[:] = [
                route for route in ctx.app.routes if id(route) not in created
            ]
            ctx.app.openapi_schema = None
