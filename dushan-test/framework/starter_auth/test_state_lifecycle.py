import asyncio

import httpx
import pytest

from framework.common.diagnostics.safe_exception_diagnostics import SafeExceptionDiagnostics
from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.auth_callback import AuthCallback
from framework.starter_cache.definitions.constants.cache_error_codes import CacheErrorCodes
from framework.starter_cache.exception.cache_exception import CacheException

from .support import ACCESS, BINDING, CHANNEL_RESPONSES, SECRET, RecordingTransport, client_config


async def callback(service, request, *, app="app-a", source="GITHUB", binding=BINDING):
    return await service.complete(
        app, source, [("state", request.state), ("code", "secret-code")], binding=binding
    )


async def test_real_state_concurrent_one_winner(harness):
    build, _, _ = harness
    transport = RecordingTransport(CHANNEL_RESPONSES["GITHUB"])
    service = await build(transport=transport)
    request = await service.begin("app-a", "GITHUB", binding=BINDING)
    results = await asyncio.gather(
        *(callback(service, request) for _ in range(48)), return_exceptions=True
    )
    winners = [r for r in results if not isinstance(r, BaseException)]
    assert len(winners) == 1 and winners[0].identity.subject == "123"
    assert len(transport.requests) == 2
    assert all(r.error_code == Codes.STATE for r in results if isinstance(r, AuthException))


@pytest.mark.parametrize(
    "attack",
    [
        "missing",
        "mutated",
        "binding",
        "application",
        "source",
        "configuration",
        "expired",
        "verifier",
    ],
)
async def test_real_state_binding_and_expiry(harness, attack):
    build, _, cache = harness
    configs = (client_config(), client_config(application_id="app-b"), client_config("GITEE"))
    transport = RecordingTransport(CHANNEL_RESPONSES["GITHUB"])
    service = await build(configs=configs, transport=transport)
    request = await service.begin("app-a", "GITHUB", binding=BINDING)
    state, app, source, binding = request.state, "app-a", "GITHUB", BINDING
    if attack == "missing":
        state = ""
    if attack == "mutated":
        state = ("X" if state[0] != "X" else "Y") + state[1:]
    if attack == "binding":
        binding = "different-browser-" + "y" * 32
    if attack == "application":
        app = "app-b"
    if attack == "source":
        source = "GITEE"
    config = service.clients._clients[("app-a", "GITHUB")]
    identifier = service.store.identifier(config, request.state)
    raw = cache.get_client(service.store.key)
    key = cache.build_full_key(service.store.key, identifier)
    if attack == "expired":
        await raw.pexpire(key, 1)
        await asyncio.sleep(0.015)
    if attack == "verifier":
        await raw.hset(key, "verifier", "invalid")
    if attack == "configuration":
        service.clients._clients[("app-a", "GITHUB")] = config.model_copy(
            update={"redirect_uri": "https://app.example/changed"}
        )
    with pytest.raises(AuthException) as failure:
        await service.complete(
            app, source, [("state", state), ("code", "secret-code")], binding=binding
        )
    assert failure.value.error_code == Codes.STATE
    assert not transport.requests
    if attack in {"binding", "application", "source", "mutated", "missing"}:
        assert (await callback(service, request)).identity.subject == "123"


async def test_denial_consumes_state_without_http(harness):
    build, _, _ = harness
    service = await build()
    request = await service.begin("app-a", "GITHUB", binding=BINDING)
    with pytest.raises(AuthException) as failure:
        await service.complete(
            "app-a",
            "GITHUB",
            [("state", request.state), ("error", "access_denied"), ("error_description", SECRET)],
            binding=BINDING,
        )
    assert failure.value.outcome == "rejected"
    assert SECRET not in str(failure.value)
    assert service._http is None
    with pytest.raises(AuthException) as failure:
        await callback(service, request)
    assert failure.value.error_code == Codes.STATE


@pytest.mark.parametrize(
    "pairs",
    [
        [("code", "first"), ("code", "second")],
        [("code", "value"), ("error", "denied")],
        [("code", "value"), ("app_id", "different")],
    ],
)
def test_callback_parameter_pollution(pairs):
    with pytest.raises(AuthException):
        AuthCallback.parse(pairs, code_parameter="code", client_id="client-a")


async def test_cache_failure_is_closed_and_safe(harness, monkeypatch):
    build, _, cache = harness
    service = await build()

    async def fail(*args, **kwargs):
        raise CacheException(CacheErrorCodes.OPERATION_FAILED, cause=RuntimeError(SECRET))

    monkeypatch.setattr(cache, "eval_atomic", fail)
    with pytest.raises(AuthException) as failure:
        await service.begin("app-a", "GITHUB", binding=BINDING)
    assert failure.value.error_code == Codes.CACHE
    assert failure.value.__cause__ is not None
    safe = SafeExceptionDiagnostics.snapshot(failure.value)
    assert SECRET not in str(safe) + repr(safe.__dict__)
    assert service._http is None


async def test_close_waits_operation_and_cancelled_waiter(harness):
    build, _, _ = harness
    entered, release = asyncio.Event(), asyncio.Event()
    requests = []

    async def handler(request):
        requests.append(request)
        if request.url.path.endswith("access_token"):
            entered.set()
            await release.wait()
            return httpx.Response(200, json={"access_token": ACCESS})
        return httpx.Response(200, json={"id": 123})

    service = await build(transport=httpx.MockTransport(handler))
    request = await service.begin("app-a", "GITHUB", binding=BINDING)
    task = asyncio.create_task(callback(service, request))
    await entered.wait()
    closer = asyncio.create_task(service.close())
    await asyncio.sleep(0)
    closer.cancel()
    with pytest.raises(asyncio.CancelledError):
        await closer
    assert not service._close_task.done() and not service._http.client.is_closed
    with pytest.raises(AuthException):
        await service.begin("app-a", "GITHUB", binding=BINDING)
    release.set()
    assert (await task).identity.subject == "123"
    await service.close()
    await service.close()
    assert service._http.client.is_closed and not service._active


async def test_cancelled_exchange_is_not_retried(harness):
    build, _, _ = harness
    entered = asyncio.Event()
    requests = []

    async def handler(request):
        requests.append(request)
        entered.set()
        await asyncio.Event().wait()

    service = await build(transport=httpx.MockTransport(handler))
    request = await service.begin("app-a", "GITHUB", binding=BINDING)
    task = asyncio.create_task(callback(service, request))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    with pytest.raises(AuthException) as failure:
        await callback(service, request)
    assert failure.value.error_code == Codes.STATE and len(requests) == 1
    await service.close()
    assert service._http.client.is_closed


async def test_multi_application_task_isolation(harness):
    build, _, _ = harness
    one = RecordingTransport(CHANNEL_RESPONSES["GITHUB"])
    two = RecordingTransport(CHANNEL_RESPONSES["GITHUB"])
    first = await build(transport=one)
    second = await build(transport=two)
    request = await first.begin("app-a", "GITHUB", binding=BINDING)
    with pytest.raises(AuthException):
        await callback(second, request)
    other = await second.begin("app-a", "GITHUB", binding=BINDING)
    results = await asyncio.gather(callback(first, request), callback(second, other))
    assert all(r.identity.subject == "123" for r in results)
    await first.close()
    assert not second._http.client.is_closed
    assert first.registry is not second.registry


async def test_real_credential_cache_isolated_and_coalesced(harness):
    build, _, _ = harness
    service = await build()
    config = client_config("WECHAT_ENTERPRISE")
    calls = 0

    async def load():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return ACCESS, 120

    values = await asyncio.gather(
        *(service.credentials.get_or_load(config, load) for _ in range(12))
    )
    assert set(values) == {ACCESS} and calls == 1
    other = config.model_copy(update={"application_id": "app-b"})
    await service.credentials.get_or_load(other, load)
    changed = config.model_copy(update={"revision": 2})
    await service.credentials.get_or_load(changed, load)
    assert calls == 3


async def test_tokens_config_binding(harness):
    build, _, _ = harness
    transport = RecordingTransport(CHANNEL_RESPONSES["GITHUB"])
    service = await build(transport=transport)
    request = await service.begin("app-a", "GITHUB", binding=BINDING)
    result = await callback(service, request)
    forged = result.tokens.model_copy(update={"client_id": "different-client"})
    with pytest.raises(AuthException) as failure:
        await service.refresh(forged)
    assert failure.value.error_code == Codes.BINDING
    assert len(transport.requests) == 2
