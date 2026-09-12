import inspect
from functools import wraps

from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.context.get_bean import get_bean


def include_deleted(function):
    """仅在当前异步业务调用期间包含软删除记录，退出时恢复作用域。"""
    if not inspect.iscoroutinefunction(function):
        raise TypeError("数据库 include_deleted 只能装饰 async 函数")

    @wraps(function)
    async def invoke(*args, **kwargs):
        with get_bean(SessionProvider).options(include_deleted=True):
            return await function(*args, **kwargs)

    return invoke
