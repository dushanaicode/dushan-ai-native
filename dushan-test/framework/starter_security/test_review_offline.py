import asyncio
from contextlib import asynccontextmanager
from contextvars import ContextVar
from types import SimpleNamespace

import pytest
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials, SecurityScopes

from framework.starter_security.core.security_service import SecurityService
from framework.starter_security.definitions.constants.security_error_codes import SecurityErrorCodes
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_security.integration.security_access import SecurityAccess
from framework.starter_security.model.request_audit import RequestAudit
from framework.starter_web.context.request_context import RequestContext


@pytest.mark.parametrize("template", [None, "/safe/{id}"])
def test_request_audit_without_route_never_uses_raw_path(template):
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/private-path-marker",
            "headers": [],
            "state": {} if template is None else {"web_route_template": template},
        }
    )
    with RequestContext.bind(request, "request", "127.0.0.1"):
        audit = RequestAudit.from_request(request, "token")
    assert audit.request_url == ("<unmatched>" if template is None else template)
    assert "private-path-marker" not in audit.request_url


async def test_missing_endpoint_policy_has_configuration_error():
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
            "state": {},
            "endpoint": lambda: None,
            "app": SimpleNamespace(state=SimpleNamespace(security=object())),
        }
    )
    with pytest.raises(SecurityException) as caught:
        await SecurityAccess()(
            request,
            SecurityScopes(),
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="x" * 32),
        )
    assert caught.value.error_code is SecurityErrorCodes.CONFIGURATION


async def test_data_scope_repeated_cancellation_preserves_async_cleanup_context():
    marker = ContextVar("data_exit_marker", default=None)
    entered, exiting, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    restored = []

    @asynccontextmanager
    async def enter(identity, *, capability=None):
        token = marker.set("data")
        try:
            yield
        finally:
            exiting.set()
            await release.wait()
            marker.reset(token)
            restored.append(marker.get())

    service = SecurityService.__new__(SecurityService)
    service._data_access = SimpleNamespace(enter=enter)

    async def work():
        async with service._data_scope(object()):
            assert marker.get() == "data"
            entered.set()
            await asyncio.Future()

    task = asyncio.create_task(work())
    try:
        await entered.wait()
        task.cancel()
        await exiting.wait()
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert restored == [None] and marker.get() is None
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)
