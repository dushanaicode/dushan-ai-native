from opentelemetry.trace import SpanKind

from framework.starter_di.decorators.components import framework
from framework.starter_di.definitions.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_monitor.core.monitor_service import MonitorService
from framework.starter_monitor.spi.monitor_provider import MonitorProvider


@framework(interface=MonitorProvider, scope=ComponentScopeEnum.SINGLETON)
class MonitorProviderAdapter(MonitorProvider):
    """把本组件拥有的追踪服务发布为 SPI，不创建第二套追踪资源。"""

    def __init__(self, service: MonitorService):
        self.service = service

    @property
    def enabled(self) -> bool:
        return self.service.settings.enabled

    def span(self, name, attributes=None, *, kind=SpanKind.INTERNAL, parent=None, start_time=None):
        return self.service.span(name, attributes, kind=kind, parent=parent, start_time=start_time)

    def extract(self, headers):
        return self.service.extract(headers)

    def inject(self, headers=None):
        return self.service.inject(headers)
