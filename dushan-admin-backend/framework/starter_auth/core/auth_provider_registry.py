import inspect
import re

from framework.starter_auth.core.auth_url_policy import AuthUrlPolicy
from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import AUTH_SOURCE_PATTERN, ProviderCapability
from framework.starter_auth.oidc.oidc_metadata import OidcMetadata
from framework.starter_auth.provider.alipay_provider import AlipayProvider
from framework.starter_auth.provider.aliyun_provider import AliyunProvider
from framework.starter_auth.provider.auth_provider import AuthProvider
from framework.starter_auth.provider.baidu_provider import BaiduProvider
from framework.starter_auth.provider.csdn_provider import CsdnProvider
from framework.starter_auth.provider.dingtalk_provider import DingtalkProvider
from framework.starter_auth.provider.dingtalk_v2_provider import DingtalkV2Provider
from framework.starter_auth.provider.douyin_provider import DouyinProvider
from framework.starter_auth.provider.eleme_provider import ElemeProvider
from framework.starter_auth.provider.feishu_provider import FeishuProvider
from framework.starter_auth.provider.gitee_provider import GiteeProvider
from framework.starter_auth.provider.github_provider import GithubProvider
from framework.starter_auth.provider.huawei_provider import HuaweiProvider
from framework.starter_auth.provider.huawei_v3_provider import HuaweiV3Provider
from framework.starter_auth.provider.jd_provider import JdProvider
from framework.starter_auth.provider.meituan_provider import MeituanProvider
from framework.starter_auth.provider.mini_program_provider import MiniProgramProvider
from framework.starter_auth.provider.qq_provider import QqProvider
from framework.starter_auth.provider.taobao_provider import TaobaoProvider
from framework.starter_auth.provider.toutiao_provider import ToutiaoProvider
from framework.starter_auth.provider.wechat_enterprise_provider import WechatEnterpriseProvider
from framework.starter_auth.provider.wechat_provider import WechatProvider
from framework.starter_auth.provider.weibo_provider import WeiboProvider
from framework.starter_auth.provider.xiaomi_provider import XiaomiProvider
from framework.starter_di.decorators.components import framework


@framework
class AuthProviderRegistry:
    """本应用内的能力目录；内置渠道与扫描发现的扩展走同一注册校验。"""

    def __init__(self):
        self._providers = {}
        self._capabilities = {}
        self._sealed = False
        for provider in (
            AlipayProvider,
            AliyunProvider,
            BaiduProvider,
            CsdnProvider,
            DingtalkProvider,
            DingtalkV2Provider,
            DouyinProvider,
            ElemeProvider,
            FeishuProvider,
            GiteeProvider,
            GithubProvider,
            HuaweiProvider,
            HuaweiV3Provider,
            JdProvider,
            MeituanProvider,
            MiniProgramProvider,
            QqProvider,
            TaobaoProvider,
            ToutiaoProvider,
            WechatEnterpriseProvider,
            WechatProvider,
            WeiboProvider,
            XiaomiProvider,
        ):
            self.register(provider)

    def register(self, provider: type[AuthProvider], *, allow_loopback_http: bool = False):
        if (
            self._sealed
            or not isinstance(provider, type)
            or not issubclass(provider, AuthProvider)
            or inspect.isabstract(provider)
        ):
            raise AuthException(Codes.CONFIG)
        if any(
            not isinstance(capability, ProviderCapability) for capability in provider.capabilities
        ):
            raise AuthException(Codes.CONFIG)
        if any(
            not inspect.iscoroutinefunction(getattr(provider, name))
            for name in ("exchange", "userinfo", "refresh", "revoke")
        ):
            raise AuthException(Codes.CONFIG)
        for capability in provider.capabilities:
            if (
                not isinstance(capability.source, str)
                or re.fullmatch(AUTH_SOURCE_PATTERN, capability.source) is None
            ):
                raise AuthException(Codes.CONFIG)
            if capability.mode not in ("browser", "native") or capability.token_kind not in (
                "access_token",
                "session_key",
                "identity",
            ):
                raise AuthException(Codes.CONFIG)
            if any(
                type(getattr(capability, name)) is not bool
                for name in ("pkce", "oidc", "refresh", "refresh_rotation", "revoke")
            ):
                raise AuthException(Codes.CONFIG)
            if capability.refresh_rotation and not capability.refresh:
                raise AuthException(Codes.CONFIG)
            if capability.oidc and capability.token_kind != "access_token":
                raise AuthException(Codes.CONFIG)
            if capability.oidc and not isinstance(provider.oidc_metadata, OidcMetadata):
                raise AuthException(Codes.CONFIG)
            for name in ("refresh", "revoke"):
                if getattr(capability, name) and getattr(provider, name) is getattr(
                    AuthProvider, name
                ):
                    raise AuthException(Codes.CONFIG)
        names = [c.source for c in provider.capabilities]
        if not names or len(names) != len(set(names)) or set(names).intersection(self._providers):
            raise AuthException(Codes.CONFIG)
        for name in provider.ENDPOINT_FIELDS:
            endpoint = inspect.getattr_static(provider, name)
            if isinstance(endpoint, property):
                continue
            if not isinstance(endpoint, str):
                raise AuthException(Codes.CONFIG)
            if endpoint:
                AuthUrlPolicy.require(endpoint, allow_loopback_http=allow_loopback_http)
        for capability in provider.capabilities:
            self._providers[capability.source] = provider
            self._capabilities[capability.source] = capability

    def discover(self, components, *, allow_loopback_http: bool = False):
        for component in components:
            if issubclass(component, AuthProvider):
                self.register(component, allow_loopback_http=allow_loopback_http)

    def seal(self):
        self._sealed = True

    def get(self, source):
        if source not in self._providers:
            raise AuthException(Codes.SOURCE)
        return self._providers[source]

    def capabilities(self):
        return tuple(self._capabilities.values())

    def capability(self, source):
        self.get(source)
        return self._capabilities[source]
