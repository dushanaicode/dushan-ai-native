from typing import Protocol

from framework.starter_mq.model.message_envelope import MessageEnvelope


class ExternalMessageAuthenticator(Protocol):
    async def authenticate(self, payload: bytes, *, destination: str) -> MessageEnvelope:
        """验证外部签名、时效及目标后规范化载荷。

        返回的 Security proof 必须由可信服务签发，消费时仍会重新验证实时授权。
        不能将外部头里的 account/tenant/capability 直接视为可信身份；重试使用框架
        认证的规范化信封，保留此原始证明与有效期，不再次提升权限。
        """
        ...
