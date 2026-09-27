from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class CaptchaService(Protocol):
    def configuration(self): ...

    async def create_captcha(self, purpose: str): ...

    async def check_captcha(self, request): ...

    async def verification(self, req_vo, purpose="login") -> bool:
        """凭证通过返回 True，业务拒绝返回 False；系统故障以异常上抛。"""
        ...
