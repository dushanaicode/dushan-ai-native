import asyncio
from collections.abc import Mapping

import httpx

from framework.starter_di.decorators.components import framework
from framework.starter_di.definitions.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_ip.config.ip_settings import IpSettings
from framework.starter_ip.definitions.constants.ip_error_codes import IpErrorCodes
from framework.starter_ip.exception.ip_exception import IpException


@framework(scope=ComponentScopeEnum.SINGLETON)
class IpLocationHttpClient:
    def __init__(self, settings: IpSettings) -> None:
        self._settings = settings
        self._client: httpx.AsyncClient | None = None
        self._close_task: asyncio.Task[None] | None = None

    def open(self) -> None:
        if self._client is not None or self._close_task is not None:
            raise RuntimeError("在线 IP 客户端不能重复打开")
        if not self._settings.online_enabled:
            raise ValueError("在线 IP 查询未启用")
        self._client = httpx.AsyncClient(
            follow_redirects=False,
            trust_env=False,
            limits=httpx.Limits(max_connections=self._settings.online_max_connections),
            timeout=self._settings.online_timeout_seconds,
        )

    async def get(
        self, provider: str, url: str, *, params: Mapping[str, str], timeout_seconds: float
    ) -> bytes:
        if self._client is None:
            raise IpException(IpErrorCodes.NOT_INITIALIZED)
        try:
            async with self._client.stream(
                "GET",
                url,
                params=params,
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                    "User-Agent": "dushan-ip/1",
                },
                timeout=min(timeout_seconds, self._settings.online_timeout_seconds),
            ) as response:
                response.raise_for_status()
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    raise IpException(
                        IpErrorCodes.QUERY_FAILED,
                        context={"provider": provider, "reason": "content_encoding"},
                    )
                content = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    if len(content) + len(chunk) > self._settings.online_max_response_bytes:
                        raise IpException(
                            IpErrorCodes.QUERY_FAILED,
                            context={"provider": provider, "reason": "response_too_large"},
                        )
                    content.extend(chunk)
                return bytes(content)
        except httpx.TimeoutException as error:
            raise IpException(
                IpErrorCodes.QUERY_FAILED, context={"provider": provider, "reason": "timeout"}
            ) from error
        except httpx.HTTPStatusError as error:
            raise IpException(
                IpErrorCodes.QUERY_FAILED, context={"provider": provider, "reason": "http_status"}
            ) from error
        except httpx.RequestError as error:
            raise IpException(
                IpErrorCodes.QUERY_FAILED, context={"provider": provider, "reason": "network"}
            ) from error

    async def close(self) -> None:
        if self._close_task is None and self._client is not None:
            client, self._client = self._client, None
            self._close_task = asyncio.create_task(client.aclose(), name="ip-http-close")
        if self._close_task is not None:
            await asyncio.shield(self._close_task)
