import asyncio
import json

import httpx

from framework.starter_captcha.config.captcha_settings import CaptchaSettings
from framework.starter_captcha.exception.captcha_error_codes import CaptchaErrorCodes as Codes
from framework.starter_captcha.exception.captcha_exception import CaptchaException


class CaptchaHttpClient:
    """只向已选厂商发送 POST，限制总时间、连接数及解码前响应字节，不隐式重试。"""

    def __init__(self, settings: CaptchaSettings) -> None:
        self.settings = settings
        self.client = httpx.AsyncClient(
            trust_env=False,
            follow_redirects=False,
            timeout=settings.cloud_timeout_seconds,
            limits=httpx.Limits(
                max_connections=settings.cloud_max_connections,
                max_keepalive_connections=settings.cloud_max_connections,
            ),
        )

    async def post(self, endpoint: str, headers: dict[str, str], body: bytes) -> dict:
        try:
            async with asyncio.timeout(self.settings.cloud_timeout_seconds):
                async with self.client.stream(
                    "POST",
                    f"https://{endpoint}/",
                    content=body,
                    headers={**headers, "accept-encoding": "identity"},
                ) as response:
                    if response.status_code != 200:
                        raise CaptchaException(Codes.PROVIDER_FAILURE)
                    if response.headers.get("content-encoding", "identity").lower() != "identity":
                        raise CaptchaException(Codes.PROVIDER_RESPONSE)
                    content = bytearray()
                    async for chunk in response.aiter_raw():
                        if len(content) + len(chunk) > self.settings.cloud_max_response_bytes:
                            raise CaptchaException(Codes.PROVIDER_RESPONSE)
                        content.extend(chunk)
                    result = json.loads(content)
                    if not isinstance(result, dict):
                        raise CaptchaException(Codes.PROVIDER_RESPONSE)
                    return result
        except (TimeoutError, httpx.TimeoutException) as error:
            raise CaptchaException(Codes.PROVIDER_TIMEOUT, cause=error) from error
        except httpx.RequestError as error:
            raise CaptchaException(Codes.PROVIDER_FAILURE, cause=error) from error
        except (ValueError, UnicodeError, RecursionError) as error:
            raise CaptchaException(Codes.PROVIDER_RESPONSE, cause=error) from error

    async def close(self) -> None:
        await self.client.aclose()
