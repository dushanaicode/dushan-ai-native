from framework.starter_di.public import (
    pre_destroy_hook,
    service,
)
from module_system.framework.sms.client.abstract_sms_client import AbstractSmsClient
from module_system.framework.sms.client.providers.aliyun_sms_client import AliyunSmsClient
from module_system.framework.sms.client.providers.debug_ding_talk_sms_client import (
    DebugDingTalkSmsClient,
)
from module_system.framework.sms.client.providers.huawei_sms_client import HuaweiSmsClient
from module_system.framework.sms.client.providers.qiniu_sms_client import QiniuSmsClient
from module_system.framework.sms.client.providers.tencent_sms_client import TencentSmsClient
from module_system.framework.sms.client.sms_client import SmsClient
from module_system.framework.sms.enums.sms_channel_enum import SmsChannelEnum
from module_system.framework.sms.factory.sms_client_factory import SmsClientFactory
from module_system.framework.sms.model.sms_channel_properties import SmsChannelProperties


@service(interface=SmsClientFactory)
class SmsClientFactoryImpl(SmsClientFactory):
    """按短信渠道配置管理客户端实例。"""

    def __init__(self) -> None:
        """初始化封装框架短信相关领域能力。"""
        self.channel_id_clients: dict[int, AbstractSmsClient] = {}
        self.channel_code_clients: dict[str, AbstractSmsClient] = {}

    def get_sms_client_by_id(self, channel_id: int) -> SmsClient | None:
        """按短信渠道编号获取客户端实例。"""
        return self.channel_id_clients.get(channel_id)

    def get_sms_client_by_code(self, channel_code: str) -> SmsClient | None:
        """按短信渠道编码获取客户端实例。"""
        return self.channel_code_clients.get(channel_code)

    def create_or_update_sms_client(self, properties: SmsChannelProperties) -> SmsClient:
        """创建或刷新框架短信客户端实例。"""
        client: AbstractSmsClient = self.channel_id_clients.get(properties.id)
        if client is None:
            concrete_client = self._create_sms_client(properties)
            concrete_client.init()
            self.channel_id_clients[concrete_client.get_id()] = concrete_client
            self.channel_code_clients[properties.code] = concrete_client
            client = concrete_client
        else:
            if client.properties.code != properties.code:
                raise ValueError("短信渠道创建后不能更换厂商，请创建新渠道")
            client.refresh(properties)
            self.channel_code_clients[properties.code] = client
        return client

    def _create_sms_client(self, properties: SmsChannelProperties) -> AbstractSmsClient:
        """根据渠道编码创建对应厂商短信客户端。"""
        enum_item = SmsChannelEnum.get_by_code(properties.code)
        if enum_item is None:
            raise ValueError(f"未知的短信渠道 code：{properties.code}")
        match enum_item:
            case SmsChannelEnum.ALIYUN:
                return AliyunSmsClient(properties)
            case SmsChannelEnum.DEBUG_DING_TALK:
                return DebugDingTalkSmsClient(properties)
            case SmsChannelEnum.TENCENT:
                return TencentSmsClient(properties)
            case SmsChannelEnum.HUAWEI:
                return HuaweiSmsClient(properties)
            case SmsChannelEnum.QINIU:
                return QiniuSmsClient(properties)
        raise ValueError(f"无法为渠道 {properties.code} 创建 SmsClient 实例")

    @pre_destroy_hook
    async def close(self):
        for client in set(self.channel_id_clients.values()):
            await client.http_client.aclose()
