import asyncio
import ipaddress
import re
import secrets
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, nullcontext

from loguru import logger
from pydantic import ValidationError

from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_captcha.config.captcha_settings import CaptchaSettings
from framework.starter_captcha.core.captcha_provider import CaptchaProvider
from framework.starter_captcha.core.captcha_store import CaptchaStore
from framework.starter_captcha.exception.captcha_error_codes import CaptchaErrorCodes as Codes
from framework.starter_captcha.exception.captcha_exception import CaptchaException
from framework.starter_captcha.model.captcha_answer import CaptchaAnswer
from framework.starter_captcha.model.captcha_challenge import CaptchaChallenge
from framework.starter_captcha.model.captcha_verification import CaptchaVerification
from framework.starter_captcha.provider.aliyun_captcha_provider import AliyunCaptchaProvider
from framework.starter_captcha.provider.captcha_http_client import CaptchaHttpClient
from framework.starter_captcha.provider.local_captcha_provider import LocalCaptchaProvider
from framework.starter_captcha.provider.tencent_captcha_provider import TencentCaptchaProvider
from framework.starter_di.decorators.components import framework
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_monitor.core.monitor_service import MonitorService


@framework(scope=ComponentScopeEnum.SINGLETON)
class CaptchaService:
    """生成挑战 → 校验答案并签发凭证 → 业务执行前一次性消费。

    purpose 由业务入口指定且须在配置白名单内；client_ip 由可信服务端入口解析。
    挑战状态只存在于 Cache，不绑定应用实例：多 worker 或多副本可以互相接续，
    部署不需要会话亲和；重启不影响仍在 TTL 内的挑战。
    受管消费者用 Inject，非受管消费者在 ApplicationContext.execution/tasks 中 get_bean。
    """

    def __init__(self, settings: CaptchaSettings, cache: CacheHandler) -> None:
        self.settings = settings
        self.store = CaptchaStore(cache, settings)
        self._provider: CaptchaProvider | None = None
        self._http: CaptchaHttpClient | None = None
        self._pool: ThreadPoolExecutor | None = None
        self._jobs: set[asyncio.Future] = set()
        self._generating = 0
        self._operations = 0
        self._idle = asyncio.Event()
        self._idle.set()
        self._closed = False
        self._close_task: asyncio.Task[None] | None = None

    def configuration(self) -> dict:
        """只公开前端需要的选择和用途，不导出完整配置。"""
        return {
            "enabled": self.settings.enabled,
            "provider": self.settings.provider,
            "purposes": self.settings.purposes,
        }

    def open(self, provider: CaptchaProvider | None = None) -> None:
        """应用资源步骤显式调用；可传入实现同一契约的 Provider 扩展。"""
        if self._closed or self._provider is not None:
            raise CaptchaException(Codes.UNAVAILABLE)
        if not self.settings.enabled:
            raise CaptchaException(Codes.DISABLED)
        # Cache 管理连接池，验证码只能复用已就绪的客户端。
        try:
            for ttl in (
                self.settings.challenge_ttl_seconds,
                self.settings.verification_ttl_seconds,
                self.settings.generation_window_seconds,
            ):
                self.store.cache.resolve_ttl_seconds(self.store.key, ttl)
            self.store.cache.get_client(self.store.key)
        except CacheException as error:
            raise CaptchaException(Codes.CACHE_UNAVAILABLE, cause=error) from error
        if provider is not None:
            self._provider = provider
        elif self.settings.provider in ("block_puzzle", "click_word"):
            self._provider = LocalCaptchaProvider(self.settings)
        else:
            self._http = CaptchaHttpClient(self.settings)
            self._provider = (
                AliyunCaptchaProvider(self.settings.aliyun, self._http)
                if self.settings.provider == "aliyun"
                else TencentCaptchaProvider(self.settings.tencent, self._http)
            )
        self._pool = ThreadPoolExecutor(
            max_workers=self.settings.generation_concurrency, thread_name_prefix="captcha"
        )

    def _require_active(self, purpose: str) -> CaptchaProvider:
        if not self.settings.enabled:
            raise CaptchaException(Codes.DISABLED)
        if self._closed or self._provider is None:
            raise CaptchaException(Codes.UNAVAILABLE)
        if not isinstance(purpose, str) or purpose not in self.settings.purposes:
            raise CaptchaException(Codes.INVALID_INPUT)
        return self._provider

    @staticmethod
    def _require_token(token: str, code) -> None:
        if not isinstance(token, str) or re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is None:
            raise CaptchaException(code)

    @contextmanager
    def _operation(self, purpose: str) -> Iterator[CaptchaProvider]:
        """登记完整操作，关闭时连同线程提交前的等待和最后一次缓存操作一起排空。"""
        provider = self._require_active(purpose)
        self._operations += 1
        self._idle.clear()
        try:
            yield provider
        finally:
            self._operations -= 1
            if self._operations == 0:
                self._idle.set()

    def _span(self, operation: str):
        if not self.settings.tracing_enabled:
            return nullcontext()
        monitor = MonitorService.current()
        if monitor is None:
            return nullcontext()
        return monitor.span(f"captcha.{operation}", {"captcha.provider": self.settings.provider})

    def _generation_finished(self, future: asyncio.Future) -> None:
        self._jobs.remove(future)
        self._generating -= 1
        error = future.exception()
        if error is not None:
            logger.warning("验证码图片生成失败：{}", type(error).__name__)

    async def create(self, purpose: str) -> CaptchaChallenge:
        with self._operation(purpose) as provider, self._span("create"):
            if self._generating >= self.settings.generation_concurrency:
                raise CaptchaException(Codes.CAPACITY)
            self._generating += 1
            submitted = False
            try:
                await self.store.reserve_generation()
                future = asyncio.get_running_loop().run_in_executor(
                    self._pool, provider.create, purpose
                )
                self._jobs.add(future)
                future.add_done_callback(self._generation_finished)
                submitted = True
                data, record = await asyncio.shield(future)
                token = secrets.token_urlsafe(32)
                await self.store.create(token, record)
                return CaptchaChallenge(
                    token=token,
                    provider=self.settings.provider,
                    purpose=purpose,
                    expires_in=self.settings.challenge_ttl_seconds,
                    data=data,
                )
            except (OSError, ValueError) as error:
                raise CaptchaException(Codes.RESOURCE, cause=error) from error
            finally:
                if not submitted:
                    self._generating -= 1

    def _parse_answer(self, value: object, client_ip: str | None) -> CaptchaAnswer:
        try:
            answer = CaptchaAnswer.model_validate(value)
            required = {
                "block_puzzle": {"points"},
                "click_word": {"points"},
                "aliyun": {"captcha_verify_param"},
                "tencent": {"ticket", "randstr"},
            }[self.settings.provider]
            if answer.model_fields_set != required or any(
                getattr(answer, name) is None for name in required
            ):
                raise ValueError("验证码字段与 Provider 不匹配")
            if answer.points is not None and len(answer.points) != (
                1 if self.settings.provider == "block_puzzle" else 3
            ):
                raise ValueError("验证码点数无效")
            if self.settings.provider == "tencent":
                if not isinstance(client_ip, str):
                    raise ValueError("腾讯验证码需要服务端取得的客户端 IP")
                ipaddress.ip_address(client_ip)
            return answer
        except (ValidationError, ValueError) as error:
            raise CaptchaException(Codes.INVALID_INPUT, cause=error) from error

    async def check(
        self, token: str, purpose: str, answer: object, *, client_ip: str | None = None
    ) -> CaptchaVerification:
        """每次已定位挑战的提交先扣次数，非法载荷和依赖失败同样不返还次数。"""
        with self._operation(purpose) as provider, self._span("check"):
            self._require_token(token, Codes.INVALID_INPUT)
            record, payload, remaining = await self.store.reserve(token, purpose)
            parsed = self._parse_answer(answer, client_ip)
            if not await provider.verify(record, parsed, client_ip):
                raise CaptchaException(Codes.EXHAUSTED if remaining == 0 else Codes.WRONG_ANSWER)
            verification = secrets.token_urlsafe(32)
            await self.store.complete(token, purpose, payload, verification)
            return CaptchaVerification(
                verification=verification,
                purpose=purpose,
                expires_in=self.settings.verification_ttl_seconds,
            )

    async def consume(self, verification: str, purpose: str) -> None:
        """业务入口在执行操作前调用；正常返回才允许继续，重复/过期/跨用途均失败。"""
        with self._operation(purpose), self._span("consume"):
            self._require_token(verification, Codes.INVALID_VERIFICATION)
            await self.store.consume(verification, purpose)

    async def close(self) -> None:
        """所有关闭调用等待同一终态任务，取消等待者不会中断实际清理。"""
        if self._close_task is None:
            self._closed = True
            self._close_task = asyncio.create_task(self._close_resources(), name="captcha-close")
        await asyncio.shield(self._close_task)

    async def _close_resources(self) -> None:
        """等完整操作及取消后仍运行的生成线程结束，再释放本应用资源。"""
        await self._idle.wait()
        if self._jobs:
            await asyncio.gather(*self._jobs, return_exceptions=True)
        self._provider = None
        if self._pool is not None:
            self._pool.shutdown(wait=True)
            self._pool = None
        if self._http is not None:
            await self._http.close()
            self._http = None
