from pathlib import Path

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_di.decorators.components import starter
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_ip.client.ip_location_http_client import IpLocationHttpClient
from framework.starter_ip.config.ip_settings import IpSettings
from framework.starter_ip.core.ip2region_database import Ip2RegionDatabase
from framework.starter_ip.service.area_service import AreaService
from framework.starter_ip.service.ip_location_service import IpLocationService


@starter(scope=ComponentScopeEnum.SINGLETON)
class IpStarter:
    """由 Native 资源步骤调用；DI 实例构造和普通导入均不读取地区或 XDB。"""

    def __init__(
        self,
        settings: IpSettings,
        areas: AreaService,
        database: Ip2RegionDatabase,
        client: IpLocationHttpClient,
        location: IpLocationService,
    ) -> None:
        self._settings = settings
        self.areas, self.database, self.location = areas, database, location
        self._client = client

    async def open(self) -> None:
        if not self._settings.enabled:
            raise ValueError("IP 组件未启用")
        self.areas.initialize(
            None if self._settings.area_csv_path is None else Path(self._settings.area_csv_path)
        )
        if self._settings.local_enabled:
            self.database.initialize(
                self._settings.local_families,
                None
                if self._settings.local_data_dir is None
                else Path(self._settings.local_data_dir),
            )
        if self._settings.online_enabled:
            self._client.open()
        self.location.open()

    async def close(self) -> None:
        errors = []
        cancellation = None
        for close, label in (
            (self.location.close, "IP 查询清理"),
            (self._client.close, "IP HTTP 客户端清理"),
        ):
            error, current_cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                close, label
            )
            if error is not None:
                errors.append(error)
            if current_cancellation is not None:
                cancellation = current_cancellation
        for close in (self.database.close, self.areas.close):
            try:
                close()
            except Exception as close_error:
                errors.append(close_error)
        CleanupUtils.raise_collected_cleanup_errors(
            "IP 资源清理失败", errors, caller_cancellation=cancellation
        )
