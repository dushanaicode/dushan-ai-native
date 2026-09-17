import pytest
from loguru import logger

from fixtures.public_web_app import create_public_app
from framework.starter_auth.config.configured_auth_clients import ConfiguredAuthClients
from framework.starter_auth.core.auth_provider_registry import AuthProviderRegistry
from framework.starter_auth.core.auth_service import AuthService
from framework.starter_auth.exception.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.starter.auth_starter import AuthStarter
from framework.starter_cache.lock.distributed_lock import DistributedLock

from .support import SECRET, client_config, settings
from .test_application import application_values


async def test_starter_logs_registration_configuration_and_real_shutdown(config_dir):
    records = []
    sink = logger.add(
        lambda message: records.append((message.record["level"].name, message.record["message"]))
    )
    try:
        app = create_public_app(base_dir=config_dir(application_values()), environ={})
        async with app.router.lifespan_context(app):
            assert app.state.auth.is_ready
            assert app.state.auth._http is None
            with app.state.application_context.execution():
                starter = app.state.application_context.get_bean(AuthStarter)
                assert starter.service is app.state.auth
        assert not starter.service.is_ready
    finally:
        logger.remove(sink)
    messages = "\n".join(message for _, message in records)
    assert "【AuthStarter 】初始化完成，第三方授权服务已就绪" in messages
    assert "【AuthStarter 】第三方授权服务已关闭" in messages
    assert "静态客户端校验完成：启用 1 个，停用 0 个" in messages
    assert any(
        level == "DEBUG" and "授权源=GITHUB" in message and "GithubProvider" in message
        for level, message in records
    )
    assert any(
        level == "DEBUG" and "缓存前缀=auth:state client=auth_store" in message
        for level, message in records
    )
    assert "【starter_auth 】" not in messages
    assert SECRET not in messages


@pytest.mark.parametrize("failure", ["unknown_source", "missing_cache"])
async def test_starter_failure_never_opens_authorization_or_reports_success(harness, failure):
    _, app, cache = harness
    client = client_config()
    if failure == "unknown_source":
        client = client.model_copy(update={"source": "UNKNOWN_SOURCE"})
    config = settings(
        clients=(client,), client_name="missing" if failure == "missing_cache" else "default"
    )
    service = AuthService(
        config,
        ConfiguredAuthClients(config),
        AuthProviderRegistry(),
        cache,
        app.state.application_context.get_bean(DistributedLock),
    )
    starter = AuthStarter(service)
    messages = []
    sink = logger.add(lambda message: messages.append(message.record["message"]))
    try:
        with pytest.raises(AuthException) as failed:
            await starter.open()
        assert failed.value.error_code == (
            Codes.CACHE if failure == "missing_cache" else Codes.SOURCE
        )
        assert not service.is_ready and service._http is None
        with pytest.raises(AuthException) as unavailable:
            await service.begin("app-a", "GITHUB", binding="not-ready")
        assert unavailable.value.error_code == Codes.UNAVAILABLE
        assert not any("【AuthStarter 】初始化完成" in message for message in messages)
    finally:
        await starter.close()
        logger.remove(sink)
    with pytest.raises(AuthException) as closed:
        await starter.open()
    assert closed.value.error_code == Codes.UNAVAILABLE
