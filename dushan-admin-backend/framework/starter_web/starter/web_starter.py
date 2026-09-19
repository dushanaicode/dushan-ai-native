from loguru import logger

from framework.starter_di.core.candidate_selection import CandidateSelection
from framework.starter_di.definitions.enums.binding_outcome_enum import BindingOutcomeEnum
from framework.starter_ip.config.ip_settings import IpSettings
from framework.starter_web.routing.controller_metadata import ControllerMetadata


class WebStarter:
    """选择活动 Controller、绑定请求入口配置并发布路由，关闭只撤销自己的声明。"""

    def __init__(self, routes):
        self.routes = routes
        self.app = routes.app
        self._created = set()

    def open(self, *, components, application, configuration):
        controllers = [item for item in components if ControllerMetadata.ATTRIBUTE in vars(item)]
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
        before = {id(route) for route in self.app.routes}
        if IpSettings in configuration.model_classes:
            self.app.state.web_trusted_proxies = configuration.get_config(
                IpSettings
            ).trusted_proxy_cidrs
        self.routes.register_controllers(
            item for item in controllers if CandidateSelection.qualified_name(item) in selected
        )
        self._created = {id(route) for route in self.app.routes if id(route) not in before}
        self.routes.seal()
        logger.debug("【WebStarter 】可信代理配置已装配，Controller 候选 {} 个", len(controllers))

    def close(self):
        self.routes.unseal()
        self.app.state.web_trusted_proxies = ()
        self.app.router.routes[:] = [
            route for route in self.app.routes if id(route) not in self._created
        ]
        self.app.openapi_schema = None
        logger.info("【WebStarter 】应用路由已撤销")
