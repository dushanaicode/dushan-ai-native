import inspect
from functools import wraps

from starlette._utils import is_async_callable

from framework.starter_web.context.http_observation import HttpObservation
from framework.starter_web.context.request_context import RequestContext
from framework.starter_web.response.result import Result


class EndpointInvocation:
    """只投影端点已返回的 Result 编码，不解析 JSON、不访问请求或响应流。"""

    @staticmethod
    def wrap(endpoint):
        if is_async_callable(endpoint):

            @wraps(endpoint)
            async def invoke(*args, **kwargs):
                result = await endpoint(*args, **kwargs)
                EndpointInvocation.observe(result)
                return result
        else:

            @wraps(endpoint)
            def invoke(*args, **kwargs):
                result = endpoint(*args, **kwargs)
                EndpointInvocation.observe(result)
                return result

        invoke.__signature__ = inspect.signature(endpoint, eval_str=True)
        return invoke

    @staticmethod
    def observe(result) -> None:
        if isinstance(result, Result):
            observation = HttpObservation.find(RequestContext.current().connection.scope)
            observation.business_code = result.code
