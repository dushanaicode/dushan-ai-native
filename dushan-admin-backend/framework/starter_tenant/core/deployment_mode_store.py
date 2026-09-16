import hashlib
import json

from sqlalchemy import false, select, update

from framework.starter_database.repository.atomic_upsert import AtomicUpsert
from framework.starter_tenant.exception.tenant_exception import TenantException
from framework.starter_tenant.model.deployment_mode_record import DeploymentModeRecord


class DeploymentModeStore:
    """先显式迁移表，再封存部署模式；冲突时不覆盖已登记的配置。"""

    def __init__(self, database, settings):
        self.database, self.settings = database, settings

    @staticmethod
    def values(settings):
        payload = {
            "enabled": settings.enabled,
            "default_tenant_id": settings.default_tenant_id,
            "profile": settings.profile.value,
            "custom_capabilities": sorted(settings.custom_capabilities),
        }
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return {
            "enabled": settings.enabled,
            "default_tenant_id": settings.default_tenant_id,
            "profile": settings.profile.value,
            "fingerprint": fingerprint,
        }

    async def claim(self):
        table = DeploymentModeRecord.__table__
        values = self.values(self.settings)
        command = AtomicUpsert(table, ("id",), ()).values(id=1, **values)
        command.access_condition = false()
        async with self.database.transaction() as session:
            await session.execute(command)
            await self.assert_current(session)

    async def assert_current(self, session):
        table = DeploymentModeRecord.__table__
        row = (
            (await session.execute(select(table).where(table.c.id == 1).with_for_update()))
            .mappings()
            .one_or_none()
        )
        if (
            row is None
            or row["deleted"]
            or row["fingerprint"] != self.values(self.settings)["fingerprint"]
        ):
            raise TenantException("mode")
        return row

    async def transition(self, desired, directory):
        """独立部署进程中执行；租户变更也必须先锁同一控制记录。"""
        table = DeploymentModeRecord.__table__
        async with self.database.transaction() as session:
            current = await self.assert_current(session)
            if current["default_tenant_id"] != desired.default_tenant_id:
                raise TenantException("mode")
            if current["enabled"] and not desired.enabled:
                if directory is None:
                    raise TenantException("configuration")
                enabled = await directory.enabled_tenant_ids()
                if not isinstance(enabled, tuple) or any(
                    not isinstance(value, str) or not value for value in enabled
                ):
                    raise TenantException("configuration")
                if set(enabled) != {desired.default_tenant_id}:
                    raise TenantException("mode")
            await session.execute(
                update(table).where(table.c.id == 1).values(**self.values(desired))
            )
