import hashlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import override

from fastapi import Request

from framework.common.contracts import SnowflakeId
from framework.starter_cache.public import CacheHandler
from framework.starter_di.public import Inject, service
from framework.starter_security.public import (
    PublicRequestContextProvider,
    SecurityErrorCodes,
    SecurityException,
)
from framework.starter_tenant.public import TenantErrorCodes, TenantException, TenantSettings
from framework.starter_web.public import RoutePolicy
from module_system.config.system_settings import SystemSettings
from module_system.controller.admin.auth.auth_cookies import AuthCookies
from module_system.dal.cache.system_cache_key_constants import SystemCacheKeyConstants
from module_system.definitions.constants.public_context_constants import PublicContextConstants
from module_system.framework.sms.sms_callback_token import SmsCallbackToken
from module_system.service.workload.system_workload_service import SystemWorkloadService


@service(interface=PublicRequestContextProvider)
class SystemPublicRequestContextProvider(PublicRequestContextProvider):
    tenant: TenantSettings = Inject()
    settings: SystemSettings = Inject()
    workloads: SystemWorkloadService = Inject()
    cache: CacheHandler = Inject()

    @override
    def validate(self, name: str) -> None:
        if name not in PublicContextConstants.NAMES:
            raise ValueError(f"未登记的公开上下文：{name}")

    @override
    def parameters(self, name: str) -> tuple[dict, ...]:
        self.validate(name)
        if name == PublicContextConstants.TENANT_SELECTION:
            return (
                {
                    "in": "header",
                    "name": RoutePolicy.TENANT_HEADER,
                    "required": self.tenant.enabled,
                    "schema": {"type": "string", "pattern": "^[1-9][0-9]{0,18}$"},
                },
            )
        if name == PublicContextConstants.SMS_CALLBACK:
            return (
                {
                    "in": "query",
                    "name": "token",
                    "required": True,
                    "schema": {"type": "string", "maxLength": 129},
                },
            )
        return (
            {
                "in": "cookie",
                "name": "system_social_binding",
                "required": True,
                "schema": {"type": "string"},
            },
        )

    def _selected_tenant(self, request: Request) -> str:
        values = request.headers.getlist(RoutePolicy.TENANT_HEADER)
        if not values:
            if not self.tenant.enabled:
                return self.tenant.default_tenant_id
            raise TenantException(TenantErrorCodes.MISSING, detail="请选择租户")
        if len(values) != 1:
            raise TenantException(TenantErrorCodes.DENIED, detail="租户请求头不能重复")
        try:
            selected = SnowflakeId.format(values[0])
        except ValueError as error:
            raise TenantException(TenantErrorCodes.DENIED, detail="租户请求头格式不正确") from error
        if not self.tenant.enabled and selected != self.tenant.default_tenant_id:
            raise TenantException(TenantErrorCodes.DENIED, detail="当前部署不允许选择其他租户")
        return selected

    @override
    @asynccontextmanager
    async def enter(self, request: Request, name: str) -> AsyncIterator[None]:
        if name != PublicContextConstants.TENANT_SELECTION and request.headers.getlist(
            RoutePolicy.TENANT_HEADER
        ):
            raise SecurityException(
                SecurityErrorCodes.DENIED, detail="该入口只从已验证凭据恢复租户"
            )
        channel_id = None
        if name == PublicContextConstants.TENANT_SELECTION:
            AuthCookies.check_origin(request, self.settings)
            tenant_id = self._selected_tenant(request)
            capability = "system.auth"
        elif name == PublicContextConstants.SOCIAL_LOGIN:
            AuthCookies.check_origin(request, self.settings)
            binding = request.cookies.get("system_social_binding")
            if binding is None or not 32 <= len(binding) <= 1024:
                raise SecurityException(SecurityErrorCodes.INVALID)
            found = await self.cache.get(
                SystemCacheKeyConstants.SOCIAL_LOGIN_TENANT,
                hashlib.sha256(binding.encode()).hexdigest(),
            )
            if not found.hit:
                raise SecurityException(SecurityErrorCodes.INVALID, detail="社交授权流程已失效")
            tenant_id = found.value
            capability = "system.auth"
        elif name == PublicContextConstants.SMS_CALLBACK:
            tokens = request.query_params.getlist("token")
            if len(tokens) != 1 or set(request.query_params) != {"token"}:
                raise SecurityException(SecurityErrorCodes.INVALID)
            tenant_id, channel_id = SmsCallbackToken.verify(
                self.settings.sms_callback_token, tokens[0]
            )
            capability = "system.sms.send"
        else:
            raise ValueError(f"未登记的公开上下文：{name}")
        async with self.workloads.scope(capability, tenant_id):
            if channel_id is not None:
                request.state.sms_callback_channel_id = channel_id
            try:
                yield
            finally:
                if channel_id is not None:
                    request.scope["state"].pop("sms_callback_channel_id")
