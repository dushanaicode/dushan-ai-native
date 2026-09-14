import asyncio
import json
import os
from pathlib import Path
from typing import Annotated

from fastapi import File, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent

from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_web.context.request_context import RequestContext
from framework.starter_web.response.file_result import FileResult
from framework.starter_web.response.result import Result
from framework.starter_web.response.stream_integrity import StreamIntegrity
from framework.starter_web.response.streaming_result import StreamingResult
from framework.starter_web.routing.decorators import controller, route
from framework.starter_web.routing.route_policy import RoutePolicy


@service
class Resource:
    def __init__(self):
        self.root = Path(os.environ["DUSHAN_WEB_EVIDENCE"])
        self.active = 0
        self.closed = False

    async def pre_destroy(self):
        self.closed = True
        (self.root / "resource-closed.json").write_text(
            json.dumps({"active_streams": self.active}), encoding="utf-8"
        )


@controller("/__web_test", policy=RoutePolicy.public())
class Endpoints:
    resource: Resource = Inject()

    @route("/info", response_model=Result[dict])
    async def info(self, request: Request):
        context = RequestContext.current()
        return Result.success(
            {
                "request_id": context.request_id,
                "ip": context.client_ip,
                "active_streams": self.resource.active,
                "engine": request.app.state.web_stream_policy.engine,
            }
        )

    @route("/protected", policy=RoutePolicy(("read",), tenant_required=True))
    async def protected(self):
        return RequestContext.current().identity

    @route("/file")
    async def file(self, request: Request):
        return FileResult(request.app.state.bootstrap.response_settings).download(
            self.resource.root / "data.bin"
        )

    @route("/head", methods=("HEAD",))
    async def head(self):
        return Response("head representation", headers={"ETag": "test"})

    @route("/echo", methods=("POST",))
    async def echo(self, request: Request):
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
        return {"bytes": size}

    @route("/upload", methods=("POST",))
    async def upload(self, file: Annotated[UploadFile, File()]):
        return {"bytes": file.size, "rolled": file.file._rolled}

    @route("/known")
    async def known(self, request: Request, excel: bool = False):
        files = FileResult(request.app.state.bootstrap.response_settings)
        data = b"known-length" * 20_000
        return (
            files.excel_stream(data, "data.xlsx") if excel else files.stream_bytes(data, "data.bin")
        )

    @route("/events", response_class=EventSourceResponse)
    async def events(self):
        yield ServerSentEvent(event="item", data={"value": 1})
        yield ServerSentEvent(event="done", data={"count": 1})

    @route("/stream", response_class=StreamingResponse)
    async def stream(
        self,
        fail: bool = False,
        declared_length: bool = False,
        before: bool = False,
        sse: bool = True,
        integrity: bool = False,
    ):
        resource = self.resource
        request_id = RequestContext.current().request_id

        async def chunks():
            resource.active += 1
            try:
                if before:
                    raise RuntimeError("password=HTTP-stream-before-secret")
                yield b"first\n"
                if fail:
                    raise RuntimeError("password=HTTP-stream-secret")
                for _ in range(100):
                    await asyncio.sleep(0.02)
                    assert not resource.closed
                    assert RequestContext.current().request_id == request_id
                    yield b"next\n"
                yield b"done\n"
            finally:
                resource.active -= 1
                (resource.root / f"stream-closed-{request_id}").write_text(
                    "closed", encoding="utf-8"
                )

        return StreamingResult(
            chunks(),
            media_type="text/event-stream" if sse else "text/plain",
            headers={"Content-Length": "9999"} if declared_length else None,
            integrity=StreamIntegrity(protocol="fixture-stream-v1", completion_marker="done\n")
            if sse or integrity
            else None,
        )
