import inspect
from functools import wraps

from framework.starter_di.context.get_bean import get_bean
from framework.starter_security.bizlog.biz_log_service import BizLogService
from framework.starter_security.bizlog.log_record_spec import LogRecordSpec
from framework.starter_security.config.security_settings import SecuritySettings


def log_record(spec: LogRecordSpec):
    """每次调用按当前应用解析；不在闭包缓存服务或拦截器。"""

    def decorate(function):
        if not inspect.iscoroutinefunction(function):
            raise TypeError("业务日志装饰器仅支持异步函数")
        signature = inspect.signature(function)
        if any(name not in signature.parameters for name in spec.capture):
            raise ValueError("日志 capture 包含不存在的参数")

        @wraps(function)
        async def wrapped(*args, **kwargs):
            if not get_bean(SecuritySettings).bizlog_enabled:
                return await function(*args, **kwargs)
            arguments = signature.bind(*args, **kwargs)
            arguments.apply_defaults()
            captured = {name: arguments.arguments[name] for name in spec.capture}
            return await get_bean(BizLogService).invoke(
                spec,
                lambda: function(*args, **kwargs),
                captured,
            )

        return wrapped

    return decorate
