import asyncio
import re

import bcrypt

from framework.common.utils.asyncio.asyncio_utils import AsyncioUtils
from framework.starter_di.decorators.components import framework
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_security.config.security_settings import SecuritySettings
from framework.starter_security.exception.security_exception import SecurityException


@framework(scope=ComponentScopeEnum.SINGLETON)
class PasswordEncoder:
    """bcrypt 2b；拒绝超长 UTF-8 密码，不截断、不预哈希、不接受弱算法。"""

    def __init__(self, settings: SecuritySettings):
        self.settings = settings
        self._limit = asyncio.Semaphore(settings.password_concurrency)
        self._active = 0
        self._idle = asyncio.Event()
        self._idle.set()
        self._closed = False

    @staticmethod
    def _password(value: str) -> bytes:
        if not isinstance(value, str):
            raise ValueError("密码必须是字符串")
        encoded = value.encode("utf-8")
        if not 1 <= len(encoded) <= 72:
            raise ValueError("密码必须为 1 到 72 个 UTF-8 字节")
        return encoded

    async def hash(self, secret: str) -> str:
        password = self._password(secret)
        return (await self._work(self._hash, password)).decode("ascii")

    def _hash(self, password: bytes) -> bytes:
        return bcrypt.hashpw(
            password, bcrypt.gensalt(rounds=self.settings.bcrypt_rounds, prefix=b"2b")
        )

    async def verify(self, plain: str, hashed: str) -> bool:
        password = self._password(plain)
        if (
            not isinstance(hashed, str)
            or re.fullmatch(r"\$2b\$(1[2-6])\$[./A-Za-z0-9]{53}", hashed) is None
        ):
            raise ValueError("密码哈希格式或安全参数无效")
        return await self._work(bcrypt.checkpw, password, hashed.encode("ascii"))

    async def _work(self, function, *args):
        if self._closed:
            raise SecurityException("closed")
        self._active += 1
        self._idle.clear()
        try:
            async with self._limit:
                # Python 线程不能被 Task.cancel 强行终止；取消也必须等真实计算结束。
                return await AsyncioUtils.run_cancellation_shielded(
                    asyncio.to_thread(function, *args)
                )
        finally:
            self._active -= 1
            if not self._active:
                self._idle.set()

    async def close(self) -> None:
        self._closed = True
        await self._idle.wait()
