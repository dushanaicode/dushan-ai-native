from typing import Protocol, runtime_checkable

from module_system.framework.sms.client.sms_client import SmsClient
from module_system.framework.sms.model.sms_channel_properties import SmsChannelProperties


@runtime_checkable
class SmsClientFactory(Protocol):
    """短信客户端工厂接口"""

    def get_sms_client_by_id(self, channel_id: int) -> SmsClient | None:
        """按短信渠道编号获取客户端。"""
        ...

    def get_sms_client_by_code(self, channel_code: str) -> SmsClient | None:
        """按短信渠道编码获取客户端。"""
        ...

    def create_or_update_sms_client(self, properties: SmsChannelProperties) -> SmsClient:
        """根据渠道配置创建或刷新短信客户端。"""
        ...
