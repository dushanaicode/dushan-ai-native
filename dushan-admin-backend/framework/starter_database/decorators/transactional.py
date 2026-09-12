import inspect
from functools import wraps

from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.context.get_bean import get_bean


def transactional(function=None, *, propagation="required", source=None):
    """在当前应用解析数据库，装饰异步业务函数；传播模式由事务入口统一校验。"""

    def decorate(target):
        if not inspect.iscoroutinefunction(target):
            raise TypeError("transactional 只能装饰 async 函数")

        @wraps(target)
        async def invoke(*args, **kwargs):
            database = get_bean(SessionProvider)
            async with database.transaction(source=source, propagation=propagation):
                return await target(*args, **kwargs)

        return invoke

    return decorate if function is None else decorate(function)
