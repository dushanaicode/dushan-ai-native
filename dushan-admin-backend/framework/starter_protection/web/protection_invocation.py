import inspect
from collections.abc import Callable

from starlette.requests import Request

from framework.starter_protection.core.protection_service import ProtectionService
from framework.starter_protection.definitions.constants.protection_error_codes import (
    ProtectionErrorCodes as Codes,
)
from framework.starter_protection.exception.protection_exception import ProtectionException
from framework.starter_protection.subject.protection_subject import ProtectionSubject
from framework.starter_web.context.request_context import RequestContext

type SubjectProvider = Callable[[inspect.BoundArguments], ProtectionSubject]
type ParameterSelector = tuple[str, ...] | Callable[[inspect.BoundArguments], object]


class ProtectionInvocation:
    """只绑定 FastAPI 已校验实参，不读 body/stream，不从身份头推断用户或租户。"""

    def __init__(
        self,
        func: Callable,
        parameters: ParameterSelector,
        subject: SubjectProvider | None,
        *,
        global_subject: bool = False,
    ):
        if not inspect.iscoroutinefunction(func):
            raise TypeError("保护装饰器只支持 async 函数")
        self.signature = inspect.signature(func, eval_str=True)
        if isinstance(parameters, tuple):
            if len(set(parameters)) != len(parameters) or any(
                name not in self.signature.parameters for name in parameters
            ):
                raise ValueError("保护参数必须是函数签名中不重复的参数名")
        elif not callable(parameters):
            raise TypeError("parameters 必须是参数名元组或已校验参数的选择器")
        self.parameters = parameters
        self.subject = subject
        self.global_subject = global_subject

    def resolve(self, args, kwargs) -> tuple[ProtectionService, ProtectionSubject, object]:
        bound = self.signature.bind(*args, **kwargs)
        bound.apply_defaults()
        request = next(
            (value for value in bound.arguments.values() if isinstance(value, Request)), None
        )
        if request is None:
            raise ProtectionException(
                Codes.INVALID, msg="Web 保护装饰器要求 Request 参数；非 Web 调用请显式使用服务"
            )
        # 每次从实际请求所属应用取服务，装饰器本身不保留应用对象。
        service = getattr(request.app.state, "protection", None)
        if service is None:
            raise ProtectionException(Codes.CLOSED)
        if self.subject is not None:
            subject = self.subject(bound)
        elif self.global_subject:
            subject = ProtectionSubject(kind="global", identifier="global")
        else:
            context = RequestContext.current()
            if context.connection.app is not request.app or context.client_ip is None:
                raise ProtectionException(Codes.INVALID, msg="匿名保护缺少当前应用的规范客户端地址")
            subject = ProtectionSubject(kind="client_ip", identifier=context.client_ip)
        values = (
            self.parameters(bound)
            if callable(self.parameters)
            else {name: bound.arguments[name] for name in self.parameters}
        )
        return service, subject, values
