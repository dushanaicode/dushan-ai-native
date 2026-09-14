from framework.starter_monitor.decorators.business_attributes import BusinessAttributes
from framework.starter_monitor.decorators.trace_decorator import TraceDecorator


class AutoTrace(TraceDecorator):
    """按真实函数签名读取显式业务标识，保留原调用参数、返回值和异常。"""

    def __init__(self, biz_id_param: str = ""):
        BusinessAttributes.validate(biz_id_param)
        self.biz_id_param = biz_id_param

    def prepare(self, monitor, span, signature, args, kwargs):
        if monitor.settings.capture_business_ids and self.biz_id_param:
            value = BusinessAttributes.read(
                self.biz_id_param, BusinessAttributes.arguments(signature, args, kwargs)
            )
            if value is not None:
                span.set_attribute("biz.id", value)
