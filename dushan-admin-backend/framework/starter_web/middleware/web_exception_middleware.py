from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.requests import ClientDisconnect, Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from framework.common.exception.exceptions.base_business_exception import BaseBusinessException
from framework.starter_web.context.http_observation import HttpObservation
from framework.starter_web.exception.exception_handler import GlobalExceptionHandler
from framework.starter_web.exception.reported_http_failure import ReportedHttpFailure


class WebExceptionMiddleware:
    """暂存响应头至首个内容事件；已提交的故障只传播中止，不伪造正常结束。"""

    def __init__(self, app: ASGIApp, handler: GlobalExceptionHandler, owner: str) -> None:
        self.app = app
        self.handler = handler
        self.owner = owner

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        pending: Message | None = None
        committed = False
        abort = False
        observation = HttpObservation.find(scope)

        async def tracked_send(message: Message) -> None:
            nonlocal pending, committed
            if message["type"] == "http.response.start":
                pending = message
                return
            if (
                message["type"] in {"http.response.body", "http.response.pathsend"}
                and pending is not None
            ):
                committed = True
                await send(pending)
                pending = None
            await send(message)

        try:
            await self.app(scope, receive, tracked_send)
        except ClientDisconnect:
            observation.disconnected = True
            return
        except Exception as error:
            request = Request(scope)
            if committed:
                observation.failed = True
                if not observation.failure_recorded:
                    await self.handler.record_internal_error(request, error)
                if not observation.complete:
                    abort = True
            else:
                if isinstance(error, HTTPException):
                    handle = self.handler.handle_http_exception
                elif isinstance(error, RequestValidationError):
                    handle = self.handler.handle_validation_exception
                elif isinstance(error, BaseBusinessException):
                    handle = self.handler.handle_business_exception
                else:
                    handle = self.handler.handle_internal_server_error
                response = await handle(request, error)
                await response(scope, receive, send)
        # 离开原异常处理块再抛出，避免宿主持有含载荷的隐式异常链。
        if abort:
            raise ReportedHttpFailure(self.owner)
