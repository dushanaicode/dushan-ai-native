from threading import RLock
from time import monotonic

from loguru import logger

from framework.common.exception.exceptions.configuration_exception import ConfigurationException
from framework.common.i18n.core.catalog import I18nCatalog
from framework.common.i18n.core.loader import I18nLoader
from framework.common.i18n.core.validator import I18nValidator


class I18nReloader:
    """按文件内容快照更新资源，失败时继续使用上一份完整版本。

    只在配置开启时创建；检查间隔由 reload_interval 控制，没有后台线程。
    实际加载字节的哈希与加载后快照必须相同才发布，能发现新增、修改和删除。
    文案加载和快照采集是同步 I/O，热更新默认关闭，适合受控开发场景。
    """

    def __init__(self, loader: I18nLoader, *, message_keys: tuple[str, ...] = ()) -> None:
        """首次严格加载稳定资源，初始化失败由应用启动流程处理。"""
        self._loader = loader
        self._message_keys = message_keys
        self._lock = RLock()
        self._catalog, self._snapshot = self._load_version()
        self._last_check = monotonic()

    @property
    def catalog(self) -> I18nCatalog:
        """返回最近一次完整发布的资源版本。"""
        with self._lock:
            return self._catalog

    def get_catalog(self) -> I18nCatalog:
        """到期后检查内容变化，更新失败时保留旧版本并等待下一次检查。"""
        with self._lock:
            now = monotonic()
            if now - self._last_check < self._loader.options.reload_interval:
                return self._catalog
            self._last_check = now
            try:
                if self._loader.snapshot() != self._snapshot:
                    catalog, snapshot = self._load_version()
                    self._catalog, self._snapshot = catalog, snapshot
                    logger.info("i18n 语言资源已更新")
            except (ConfigurationException, OSError) as error:
                logger.warning("i18n 热更新失败，继续使用上一版本：{}", error)
            return self._catalog

    def _load_version(self) -> tuple[I18nCatalog, dict[str, str]]:
        """仅返回与同一文件内容快照对应、通过完整性策略检查的 Catalog。"""
        catalog, loaded_snapshot = self._loader.load_version()
        I18nValidator.validate(catalog, self._message_keys)
        after = self._loader.snapshot()
        if loaded_snapshot != after:
            raise ConfigurationException(msg="i18n 资源在加载期间发生变化，请重新加载")
        return catalog, after
