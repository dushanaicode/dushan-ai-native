import asyncio
import base64
import hashlib
import re
import secrets
from collections.abc import Iterable
from contextlib import asynccontextmanager, nullcontext

from loguru import logger
from pydantic import ValidationError

from framework.starter_auth.config.auth_settings import AuthSettings
from framework.starter_auth.core.auth_credential_store import AuthCredentialStore
from framework.starter_auth.core.auth_http_client import AuthHttpClient
from framework.starter_auth.core.auth_provider_registry import AuthProviderRegistry
from framework.starter_auth.core.auth_state_store import AuthStateStore
from framework.starter_auth.core.auth_url_policy import AuthUrlPolicy
from framework.starter_auth.exception.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.auth_callback import AuthCallback
from framework.starter_auth.model.auth_flow import AuthFlow
from framework.starter_auth.model.auth_result import AuthResult
from framework.starter_auth.model.auth_tokens import AuthTokens
from framework.starter_auth.model.authorization_request import AuthorizationRequest
from framework.starter_auth.oidc.oidc_verifier import OidcVerifier
from framework.starter_auth.spi.auth_client_provider import AuthClientProvider
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.lock.distributed_lock import DistributedLock
from framework.starter_di.decorators.components import framework
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_monitor.core.monitor_service import MonitorService


@framework(scope=ComponentScopeEnum.SINGLETON)
class AuthService:
    """第三方授权的异步入口；begin/complete、userinfo、refresh/revoke 共享同一核心。

    binding 必须来自业务管理的安全浏览器会话或一次性 cookie。回调参数使用
    query/form.multi_items()，使重复字段可见。返回结果只证明外部身份，业务通过
    SocialAccountBinding 自行处理已鉴权账号的绑定，不自动创建本站会话。
    """

    def __init__(
        self,
        settings: AuthSettings,
        clients: AuthClientProvider,
        registry: AuthProviderRegistry,
        cache: CacheHandler,
        locks: DistributedLock,
    ):
        self.settings = settings.model_copy(deep=True)
        self.clients, self.registry = clients, registry
        self.store = AuthStateStore(cache, self.settings)
        self.credentials = AuthCredentialStore(cache, locks, self.settings)
        self._http = None
        self._oidc = None
        self._transport = None
        self._phase = "new"
        self._loop = None
        self._active = set()
        self._idle = asyncio.Event()
        self._idle.set()
        self._close_task = None

    @asynccontextmanager
    async def startup(self, *, transport=None):
        """向 Starter 提供一次装配窗口，成功退出后才允许授权操作。"""
        if self._phase != "new":
            raise AuthException(Codes.UNAVAILABLE)
        if not self.settings.enabled:
            raise AuthException(Codes.DISABLED)
        self._phase = "starting"
        self._loop = asyncio.get_running_loop()
        yield
        self._transport = transport
        self._phase = "ready"

    @asynccontextmanager
    async def _operation(self, source, operation):
        if not self.settings.enabled:
            raise AuthException(Codes.DISABLED)
        if self._phase != "ready" or asyncio.get_running_loop() is not self._loop:
            raise AuthException(Codes.UNAVAILABLE)
        self.registry.get(source)
        task = asyncio.current_task()
        if task in self._active:
            raise AuthException(Codes.UNAVAILABLE)
        self._active.add(task)
        self._idle.clear()
        try:
            with self._span(source, operation):
                async with asyncio.timeout(self.settings.operation_timeout_seconds):
                    yield
        except TimeoutError as error:
            raise AuthException(Codes.TIMEOUT, outcome="unknown", cause=error) from error
        except ValidationError as error:
            raise AuthException(Codes.RESPONSE, outcome="unknown", cause=error) from error
        finally:
            self._active.remove(task)
            if not self._active:
                self._idle.set()

    def _span(self, source, operation):
        monitor = MonitorService.current() if self.settings.tracing_enabled else None
        return (
            nullcontext()
            if monitor is None
            else monitor.span(
                f"auth.{operation}",
                {"auth.source": source},
            )
        )

    async def _provider(self, application_id, source):
        config = await self.clients.get_client(application_id, source)
        if config is None:
            raise AuthException(Codes.CONFIG)
        if (config.application_id, config.source) != (application_id, source):
            raise AuthException(Codes.BINDING)
        if not config.enabled:
            raise AuthException(Codes.DISABLED)
        config = config.model_copy(deep=True)
        provider_class = self.registry.get(source)
        provider_class.validate_client(config, self.settings)
        provider = provider_class(config, self._http, self.credentials, self._oidc)
        provider.validate_endpoints(self.settings)
        return provider

    def _connect_provider(self, provider):
        if self._http is None:
            self._http = AuthHttpClient(self.settings, transport=self._transport)
            self._oidc = OidcVerifier(self._http, self.settings)
        provider.http, provider.oidc = self._http, self._oidc

    async def begin(
        self, application_id: str, source: str, *, binding: str
    ) -> AuthorizationRequest:
        async with self._operation(source, "begin"):
            provider = await self._provider(application_id, source)
            capability = provider.capability
            flow = AuthFlow(
                state=secrets.token_hex(32),
                verifier=secrets.token_urlsafe(48) if capability.pkce else "",
                nonce=secrets.token_urlsafe(32) if capability.oidc else "",
            )
            challenge = (
                base64.urlsafe_b64encode(hashlib.sha256(flow.verifier.encode()).digest())
                .rstrip(b"=")
                .decode()
                if capability.pkce
                else ""
            )
            url = provider.authorize(flow, challenge) if capability.mode == "browser" else None
            if url is not None:
                AuthUrlPolicy.require(
                    url,
                    allow_loopback_http=self.settings.allow_loopback_http,
                    query=True,
                    fragment=True,
                )
            await self.store.create(provider.config, binding, flow)
            return AuthorizationRequest(
                url=url, state=flow.state, expires_in=self.settings.state_ttl_seconds
            )

    async def complete(
        self,
        application_id: str,
        source: str,
        parameters: Iterable[tuple[str, str]],
        *,
        binding: str,
    ) -> AuthResult:
        async with self._operation(source, "complete"):
            # 校验和消费完成前不创建 HTTP 资源，也不调用厂商 API。
            provider = await self._provider(application_id, source)
            callback = AuthCallback.parse(
                parameters,
                code_parameter=provider.callback_code,
                client_id=provider.config.client_id,
            )
            flow = await self.store.consume(provider.config, binding, callback.state)
            self._validate_flow(flow, provider.capability)
            if callback.denied:
                raise AuthException(Codes.REJECTED, outcome="rejected")
            self._connect_provider(provider)
            tokens = await provider.exchange(callback.code, flow)
            provider.validate_tokens(tokens, oidc_exchange=True)
            self._check_tokens(provider, tokens, outcome="unknown")
            try:
                identity = await provider.userinfo(tokens)
            except AuthException as error:
                raise AuthException(error.error_code, outcome="unknown", cause=error) from error
            self._check_tokens(provider, identity, outcome="unknown")
            tokens = tokens.model_copy(
                update={
                    "subject": identity.subject,
                    "subject_type": identity.subject_type,
                    "union_id": identity.union_id,
                }
            )
            return AuthResult(identity=identity, tokens=tokens)

    @staticmethod
    def _validate_flow(flow, capability):
        if capability.pkce:
            if re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", flow.verifier) is None:
                raise AuthException(Codes.STATE)
        elif flow.verifier:
            raise AuthException(Codes.STATE)
        if capability.oidc:
            if re.fullmatch(r"[A-Za-z0-9_-]{43}", flow.nonce) is None:
                raise AuthException(Codes.STATE)
        elif flow.nonce:
            raise AuthException(Codes.STATE)

    @staticmethod
    def _check_tokens(provider, tokens, *, outcome="not_sent"):
        config = provider.config
        if (tokens.application_id, tokens.source, tokens.client_id) != (
            config.application_id,
            config.source,
            config.client_id,
        ):
            raise AuthException(Codes.BINDING, outcome=outcome)

    async def userinfo(self, tokens: AuthTokens):
        async with self._operation(tokens.source, "userinfo"):
            provider = await self._provider(tokens.application_id, tokens.source)
            self._check_tokens(provider, tokens)
            provider.validate_tokens(tokens, outcome="not_sent")
            self._connect_provider(provider)
            identity = await provider.userinfo(tokens)
            self._check_tokens(provider, identity)
            return identity

    async def refresh(self, tokens: AuthTokens) -> AuthTokens:
        async with self._operation(tokens.source, "refresh"):
            if not self.registry.capability(tokens.source).refresh:
                raise AuthException(Codes.UNSUPPORTED)
            provider = await self._provider(tokens.application_id, tokens.source)
            self._check_tokens(provider, tokens)
            if provider.capability.oidc and not tokens.subject:
                raise AuthException(Codes.INPUT)
            self._connect_provider(provider)
            refreshed = await provider.refresh(tokens)
            provider.validate_tokens(refreshed)
            self._check_tokens(provider, refreshed, outcome="unknown")
            if provider.capability.refresh_rotation and refreshed.refresh_token is None:
                raise AuthException(Codes.RESPONSE, outcome="unknown")
            if (refreshed.subject is not None and refreshed.subject != tokens.subject) or (
                refreshed.subject_type is not None
                and tokens.subject_type is not None
                and refreshed.subject_type != tokens.subject_type
            ):
                raise AuthException(Codes.BINDING, outcome="unknown")
            updates = {
                "subject": tokens.subject,
                "subject_type": tokens.subject_type,
                "union_id": tokens.union_id,
            }
            if refreshed.refresh_token is None:
                # 非轮换渠道遵循 RFC 6749 的省略语义；轮换渠道必须返回新凭据。
                updates["refresh_token"] = tokens.refresh_token
            return refreshed.model_copy(update=updates)

    async def revoke(self, tokens: AuthTokens) -> None:
        async with self._operation(tokens.source, "revoke"):
            if not self.registry.capability(tokens.source).revoke:
                raise AuthException(Codes.UNSUPPORTED)
            provider = await self._provider(tokens.application_id, tokens.source)
            self._check_tokens(provider, tokens)
            self._connect_provider(provider)
            await provider.revoke(tokens)

    async def close(self):
        if self._loop is not None and asyncio.get_running_loop() is not self._loop:
            raise AuthException(Codes.UNAVAILABLE)
        if asyncio.current_task() in self._active:
            raise AuthException(Codes.UNAVAILABLE)
        if self._close_task is None:
            self._phase = "closing"
            self._close_task = asyncio.create_task(self._shutdown(), name="auth-close")
            self._close_task.add_done_callback(self._closed)
        await asyncio.shield(self._close_task)

    async def _shutdown(self):
        await self._idle.wait()
        if self._http is not None:
            await self._http.close()
        self._oidc = None
        self._phase = "closed"

    @staticmethod
    def _closed(task):
        if not task.cancelled() and task.exception() is not None:
            logger.error(
                "【AuthStarter 】第三方授权资源关闭失败：{}", type(task.exception()).__name__
            )

    @property
    def is_ready(self):
        return self._phase == "ready"
