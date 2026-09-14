from functools import wraps

from framework.starter_protection.lock.lock_rule import LockRule
from framework.starter_protection.web.protection_invocation import (
    ParameterSelector,
    ProtectionInvocation,
    SubjectProvider,
)


def distributed_lock(
    operation: str,
    *,
    parameters: ParameterSelector,
    subject: SubjectProvider | None = None,
    rule: LockRule | None = None,
):
    """默认按全局资源互斥；租户或主体维度须由可信提供者显式提供。"""

    def decorate(func):
        invocation = ProtectionInvocation(func, parameters, subject, global_subject=True)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            service, identity, values = invocation.resolve(args, kwargs)
            async with service.locks.hold(operation, identity, values, rule=rule):
                return await func(*args, **kwargs)

        wrapper.__signature__ = invocation.signature
        return wrapper

    return decorate
