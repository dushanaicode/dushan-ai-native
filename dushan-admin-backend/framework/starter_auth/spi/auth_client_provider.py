from abc import ABC, abstractmethod

from framework.starter_auth.config.auth_client_config import AuthClientConfig


class AuthClientProvider(ABC):
    """业务配置存储 SPI；返回当前应用、来源的有效快照，查无配置返回 None。"""

    @abstractmethod
    async def get_client(self, application_id: str, source: str) -> AuthClientConfig | None:
        pass
