from functools import wraps

from framework.starter_protection.idempotent.idempotency_rule import IdempotencyRule
from framework.starter_protection.web.protection_invocation import (
    ParameterSelector,
    ProtectionInvocation,
    SubjectProvider,
)


def idempotent(
    operation: str,
    *,
    parameters: ParameterSelector,
    subject: SubjectProvider | None = None,
    rule: IdempotencyRule | None = None,
    release_on: tuple[type[Exception], ...] = (),
):
    """防重复提交与幂等屏障共用入口；只选择业务参数，保留原始返回值和异常。"""
    if any(not issubclass(kind, Exception) or kind is Exception for kind in release_on):
        raise ValueError("release_on 必须显式指定无副作用异常类型")

    def decorate(func):
        invocation = ProtectionInvocation(func, parameters, subject)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            service, identity, values = invocation.resolve(args, kwargs)
            async with service.idempotency.guard(
                operation, identity, values, rule=rule, release_on=release_on
            ):
                return await func(*args, **kwargs)

        wrapper.__signature__ = invocation.signature
        return wrapper

    return decorate
