import asyncio
import hashlib

from framework.common.exception import (
    IllegalArgumentException,
)
from framework.common.page import DataPaginator, PageSettings
from framework.starter_cache.config.cache_settings import CacheSettings
from framework.starter_cache.core.cache_key_registry import CacheKeyRegistry
from framework.starter_cache.core.cache_key_resolver import CacheKeyResolver
from framework.starter_cache.public import CacheHandler
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_job.public import JobSettings
from framework.starter_mq.config.mq_settings import MQSettings
from framework.starter_security.public import SecuritySettings
from module_infra.controller.admin.cache.vo.cache.cache_cleanup_preset_resp_vo import (
    CacheCleanupPresetRespVO,
)
from module_infra.controller.admin.cache.vo.cache.cache_db_info_resp_vo import CacheDbInfoRespVO
from module_infra.controller.admin.cache.vo.cache.cache_info_resp_vo import CacheInfoRespVO
from module_infra.convert.cache.cache_convert import CacheConvert
from module_infra.dal.cache.cache.cache_monitor_dao import CacheMonitorDAO
from module_infra.service.cache.cache_service import CacheService


@service(interface=CacheService)
class CacheServiceImpl(CacheService):
    BUSINESS_KEYS = frozenset(
        {
            "system:dept_children_ids",
            "system:role",
            "system:user_role_ids",
            "system:user_menu_ids",
            "system:menu_role_ids",
            "system:permission_menu_ids",
            "system:oauth_client",
            "system:notify_template",
            "system:mail_account",
            "system:mail_template",
            "system:sms_template",
            "system:wxa_subscribe_template",
            "system:social_client",
            "system:tenant_package",
            "infra:monitor_redis_info",
            "security:permissions",
        }
    )
    AUTHENTICATION_KEYS = frozenset(
        {
            "system:qr_login",
            "system:social_callback_relay",
            "system:social_login_tenant",
            "system:email_password_reset",
            "system:sms_code_attempts",
            "system:websocket_ticket",
            "system:oauth2_access_token",
            "auth:state",
            "auth:credential",
        }
    )
    monitor: CacheMonitorDAO = Inject()
    registry: CacheKeyRegistry = Inject()
    cache: CacheHandler = Inject()
    pages: PageSettings = Inject()
    settings: CacheSettings = Inject()
    mq_settings: MQSettings = Inject()
    job_settings: JobSettings = Inject()
    security_settings: SecuritySettings = Inject()

    def _cleanup_targets(self, preset: str, db_name: str):
        if db_name not in {client.name for client in self.settings.clients}:
            raise IllegalArgumentException(msg="Redis 连接未配置")
        if preset in {"business", "authentication"}:
            names = self.BUSINESS_KEYS if preset == "business" else self.AUTHENTICATION_KEYS
            keys = [
                key
                for key in self.registry.get_all().values()
                if key.key in names and key.client_name == db_name
            ]
            return keys, [], []
        if preset == "mq":
            key = self.mq_settings.cache_key()
            if key.client_name != db_name:
                return [], [], []
            app_hash = hashlib.sha256(self.security_settings.application_id.encode()).hexdigest()[
                :16
            ]
            prefix = self.cache.build_full_key(key, f"{self.mq_settings.namespace}.{app_hash}")
            return [], [prefix + ":*"], []
        if preset == "jobs":
            key = self.job_settings.owner_key()
            if key.client_name != db_name:
                return [], [], []
            return [], [], [self.cache.build_full_key(key, self.job_settings.namespace)]
        raise IllegalArgumentException(msg="未知的清理预设")

    async def get_cleanup_presets(self, db_name: str) -> list[CacheCleanupPresetRespVO]:
        definitions = (
            (
                "business",
                "业务缓存（可重建）",
                "当前租户及全局已登记的可回源缓存；不删除用户、令牌、MQ消息或任务状态。清理后首次读取会重新加载。",
                False,
            ),
            (
                "authentication",
                "用户认证票据",
                "清理当前租户验证码状态及全局认证票据缓存，扫码/授权等可能需要重试；不删除数据库用户和持久会话。",
                True,
            ),
            (
                "mq",
                "当前应用 MQ 状态",
                "清理当前应用的消息流、延迟重试、死信和消费去重状态，未完成消息可能丢失，消费者将重建连接。",
                True,
            ),
            (
                "jobs",
                "当前调度租约",
                "清理当前任务调度命名空间的所有权租约，触发重新竞选；不删除数据库任务定义、请求和执行日志。",
                True,
            ),
        )
        result = []
        for code, title, description, high_risk in definitions:
            keys, patterns, exact = self._cleanup_targets(code, db_name)
            targets = (
                [CacheKeyResolver.build_prefix_pattern(key) for key in keys] + patterns + exact
            )
            result.append(
                CacheCleanupPresetRespVO(
                    code=code,
                    title=title,
                    description=description,
                    high_risk=high_risk,
                    available=bool(targets),
                    patterns=targets,
                )
            )
        return result

    async def cleanup_preset(self, preset: str, db_name: str) -> int:
        keys, patterns, exact = self._cleanup_targets(preset, db_name)
        if not keys and not patterns and not exact:
            raise IllegalArgumentException(msg="当前连接没有该预设的已登记数据")
        deleted = 0
        for key in keys:
            # 保留现有失效栅栏，阻止清理前的回源任务写回旧缓存。
            deleted += await self.cache.delete_all(key)
        for pattern in patterns:
            deleted += await self.monitor.delete_matching(db_name, pattern)
        deleted += await self.monitor.delete_keys(exact, db_name)
        return deleted

    def _key(self, name):
        key = self.registry.find(name)
        if key is None:
            raise IllegalArgumentException(msg="缓存名称未注册")
        return key

    async def get_cache_monitor_info(self):
        info, size, stats = await asyncio.gather(
            self.monitor.get_redis_info(),
            self.monitor.get_db_size(),
            self.monitor.get_command_stats(),
        )
        return CacheConvert.build_monitor_info(info, size, stats)

    async def get_cache_names(self, page_param=None):
        rows = [
            CacheInfoRespVO(cache_name=name, cache_key="", cache_value=key.remark)
            for name, key in self.registry.get_all().items()
        ]
        return DataPaginator(self.pages).paginate_list(rows, page_param)

    async def get_cache_keys(self, cache_name, page_param=None):
        key = self._key(cache_name)
        rows = await self.monitor.scan_keys(
            CacheKeyResolver.build_prefix_pattern(key), key.client_name
        )
        return DataPaginator(self.pages).paginate_list(rows, page_param)

    async def get_cache_value(self, cache_name, cache_key):
        key = self._key(cache_name)
        if not cache_key.startswith(CacheKeyResolver.build_prefix(key) + ":"):
            raise IllegalArgumentException(msg="键不属于当前缓存命名空间")
        return CacheInfoRespVO(
            cache_name=cache_name,
            cache_key=cache_key,
            cache_value=await self.monitor.get_value(cache_key, key.client_name),
        )

    async def clear_cache_by_name(self, cache_name):
        await self.cache.delete_all(self._key(cache_name))

    async def clear_cache_by_key(self, cache_key_pattern):
        for client in self.settings.clients:
            await self.monitor.delete_keys([cache_key_pattern], client.name)

    async def clear_all_caches(self):
        await asyncio.gather(
            *(self.monitor.flush_db(client.name) for client in self.settings.clients)
        )

    async def get_db_list(self):
        stats = await self.monitor.get_all_client_stats()
        return [
            CacheDbInfoRespVO(
                name=client.name,
                db_index=client.db,
                label=f"{client.name} (DB {client.db})",
                key_count=stats[client.name]["dbsize"],
            )
            for client in self.settings.clients
        ]

    async def scan_db_keys(self, db_name, pattern="*"):
        return await self.monitor.scan_all_keys_in_db(db_name, pattern)

    async def get_key_detail(self, db_name, key):
        return await self.monitor.get_key_detail(db_name, key)

    async def delete_key(self, db_name, key):
        return bool(await self.monitor.delete_raw_key(db_name, key))
