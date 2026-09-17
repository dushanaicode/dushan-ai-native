import asyncio
import time
from collections import deque

import httpx
from loguru import logger

from module_system.framework.notification.delivery.delivery_attempt import (
    DeliveryRequestStartedCallback,
)
from module_system.framework.notification.delivery.delivery_definite_failure import (
    DeliveryDefiniteFailure,
)
from module_system.framework.sms.client.sms_client import SmsClient
from module_system.framework.sms.model.sms_channel_properties import SmsChannelProperties


class AbstractSmsClient(SmsClient):
    """
    短信客户端的抽象类，提供模板方法，减少子类的冗余代码

    内置能力：
    - 共享 httpx.AsyncClient（连接池复用）
    - 并发控制（信号量），防止同时发起过多请求导致超时
    - 滑动窗口限流，防止超出渠道 API 速率限制
    - 建连异常自动重试；请求发出后的结果未知异常不重试
    """

    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: float = 1.0
    MAX_CONCURRENT_REQUESTS: int = 5
    RETRYABLE_EXCEPTIONS: tuple = (httpx.ConnectTimeout, httpx.ConnectError, httpx.PoolTimeout)
    RATE_LIMIT_MAX_REQUESTS: int = 0
    RATE_LIMIT_WINDOW_SECONDS: float = 60.0

    def __init__(self, properties: SmsChannelProperties):
        """初始化时传入短信渠道配置"""
        self.properties: SmsChannelProperties = properties
        self._http_client: httpx.AsyncClient = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=15.0, read=10.0, write=5.0, pool=10.0),
            limits=httpx.Limits(
                max_connections=20, max_keepalive_connections=10, keepalive_expiry=30
            ),
            transport=httpx.AsyncHTTPTransport(retries=2),
        )
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)
        self._rate_limit_timestamps: deque[float] = deque()
        self._rate_limit_lock: asyncio.Lock = asyncio.Lock()

    @property
    def http_client(self) -> httpx.AsyncClient:
        """供子类使用的共享 HTTP 客户端"""
        return self._http_client

    def init(self) -> None:
        """初始化方法（模板方法），打印初始化完成日志。此方法不建议被子类重写。"""
        logger.debug("短信渠道 {} 初始化完成", self.properties.id)

    def refresh(self, properties: SmsChannelProperties) -> None:
        """刷新配置，如果新配置与当前配置不同，则更新配置并重新初始化"""
        if properties == self.properties:
            return
        logger.info("短信渠道 {} 配置更新", properties.id)
        self.properties = properties
        self.init()

    def get_id(self) -> int | None:
        """获得短信渠道的编号"""
        return self.properties.id

    async def _acquire_rate_limit(self, context: str = "") -> None:
        """滑动窗口限流：等待直到可用令牌"""
        if self.RATE_LIMIT_MAX_REQUESTS <= 0:
            return
        class_name = type(self).__name__
        async with self._rate_limit_lock:
            now = time.monotonic()
            window_start = now - self.RATE_LIMIT_WINDOW_SECONDS
            while self._rate_limit_timestamps and self._rate_limit_timestamps[0] <= window_start:
                self._rate_limit_timestamps.popleft()
            if len(self._rate_limit_timestamps) >= self.RATE_LIMIT_MAX_REQUESTS:
                oldest = self._rate_limit_timestamps[0]
                wait_seconds = oldest + self.RATE_LIMIT_WINDOW_SECONDS - now + 0.1
                if wait_seconds > 0:
                    logger.debug(
                        "【{}】触发限流 ({}/{} 请求/{}秒), {}, 等待 {:.1f}秒",
                        class_name,
                        len(self._rate_limit_timestamps),
                        self.RATE_LIMIT_MAX_REQUESTS,
                        self.RATE_LIMIT_WINDOW_SECONDS,
                        context,
                        wait_seconds,
                    )
                    self._rate_limit_lock.release()
                    try:
                        await asyncio.sleep(wait_seconds)
                    finally:
                        await self._rate_limit_lock.acquire()
                    now = time.monotonic()
                    window_start = now - self.RATE_LIMIT_WINDOW_SECONDS
                    while (
                        self._rate_limit_timestamps
                        and self._rate_limit_timestamps[0] <= window_start
                    ):
                        self._rate_limit_timestamps.popleft()
            self._rate_limit_timestamps.append(time.monotonic())

    async def execute_with_retry(
        self,
        coroutine_func,
        *,
        context: str = "",
        on_request_started: DeliveryRequestStartedCallback | None = None,
    ) -> httpx.Response:
        """带限流、并发控制和重试的 HTTP 请求执行器"""
        await self._acquire_rate_limit(context)
        last_exception = None
        class_name = type(self).__name__
        async with self._semaphore:
            if on_request_started is not None:
                await on_request_started()
                try:
                    return await coroutine_func()
                except self.RETRYABLE_EXCEPTIONS as error:
                    logger.warning(
                        "【{}】连接阶段失败，由持久化消息重试: {}, error={}",
                        class_name,
                        context,
                        type(error).__name__,
                    )
                    raise DeliveryDefiniteFailure(str(error)) from error
            for attempt in range(1, self.MAX_RETRIES + 1):
                try:
                    return await coroutine_func()
                except self.RETRYABLE_EXCEPTIONS as e:
                    last_exception = e
                    if attempt < self.MAX_RETRIES:
                        logger.warning(
                            "【{}】网络异常(第{}次), {}, 错误: {}, {}秒后重试",
                            class_name,
                            attempt,
                            context,
                            type(e).__name__,
                            self.RETRY_DELAY_SECONDS,
                        )
                        await asyncio.sleep(self.RETRY_DELAY_SECONDS)
                    else:
                        logger.error(
                            "【{}】网络异常(已重试{}次仍失败), {}, 错误: {}",
                            class_name,
                            self.MAX_RETRIES,
                            context,
                            type(e).__name__,
                        )
        raise DeliveryDefiniteFailure(str(last_exception)) from last_exception

    @staticmethod
    def raise_for_definite_http_failure(response: httpx.Response) -> None:
        """把已收到的明确 HTTP 拒绝转换为可重试失败。"""
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise DeliveryDefiniteFailure(
                f"HTTP {response.status_code}: {response.text}"
            ) from error
