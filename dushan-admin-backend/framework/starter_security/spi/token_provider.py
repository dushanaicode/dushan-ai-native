from typing import Protocol

from framework.starter_security.model.login_session import LoginSession


class TokenProvider(Protocol):
    """本站令牌存储接点，由 System/业务实现，第三方 Auth 不实现此接口。

    resolve 必须按摘要、应用、认证域查询当前会话及账号，从主库或具有同等
    一致性的存储取得撤销、会话族和凭据版本；存储故障抛出原始异常。
    revoke 必须持久撤销整个 family，并使后续 resolve 立即反映撤销。
    签发、轮换 refresh Cookie、退出端点、Origin 校验由业务服务负责。
    """

    async def resolve(
        self, token_digest: str, *, application_id: str, domain: str
    ) -> LoginSession | None: ...

    async def revoke(self, session: LoginSession) -> None: ...
