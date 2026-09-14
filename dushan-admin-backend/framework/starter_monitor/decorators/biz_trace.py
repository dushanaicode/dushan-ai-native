from framework.starter_monitor.decorators.business_attributes import BusinessAttributes
from framework.starter_monitor.decorators.trace_decorator import TraceDecorator


class BizTrace(TraceDecorator):
    """记录显式业务标识及当前数据库作用域新生成的ID，不创建或清空ID上下文。"""

    def __init__(self, operation_name: str = "", id_expr: str = "", type_expr: str = ""):
        BusinessAttributes.validate(id_expr)
        BusinessAttributes.validate(type_expr)
        self.operation_name, self.id_expr, self.type_expr = operation_name, id_expr, type_expr

    def prepare(self, monitor, span, signature, args, kwargs):
        if monitor.settings.capture_business_ids and (self.id_expr or self.type_expr):
            arguments = BusinessAttributes.arguments(signature, args, kwargs)
            for key, expression in (("biz.id", self.id_expr), ("biz.type", self.type_expr)):
                value = BusinessAttributes.read(expression, arguments)
                if value is not None:
                    span.set_attribute(key, value)
        if monitor.settings.capture_generated_ids and monitor.database is not None:
            frame = monitor.database.context.current()
            if frame is not None:
                return frame, len(frame.generated_ids)
        return None

    def finish(self, monitor, span, state):
        if state is not None:
            frame, start = state
            if frame.active:
                span.set_attribute(
                    "biz.generated_ids",
                    frame.generated_ids[start : start + monitor.settings.max_generated_ids],
                )
