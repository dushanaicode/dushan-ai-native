from abc import ABC, abstractmethod

from framework.starter_auth.model.external_identity import ExternalIdentity


class SocialAccountBinding(ABC):
    """业务拥有绑定事务与权限校验；Auth 不主动调用绑定或决定账号合并。"""

    @abstractmethod
    async def find_account(self, identity: ExternalIdentity) -> str | None:
        pass

    @abstractmethod
    async def bind(self, account_id: str, identity: ExternalIdentity) -> None:
        pass

    @abstractmethod
    async def unbind(self, account_id: str, identity: ExternalIdentity) -> None:
        pass
