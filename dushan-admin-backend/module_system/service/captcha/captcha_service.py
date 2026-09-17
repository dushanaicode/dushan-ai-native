from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class CaptchaService(Protocol):
    async def create_captcha(self, purpose: str): ...

    async def check_captcha(self, request): ...

    async def verification(self, req_vo, purpose="login") -> bool: ...
