from loguru import logger

from framework.common.enums.component_type_enum import ComponentTypeEnum
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_config.provider.config_provider import ConfigProvider
from framework.starter_scanner.core.scan_result import ScanResult


class ConfigStarter:
    """从定义快照选择配置模型，管理应用配置快照的创建与释放。"""

    def open(self, bootstrap: BootstrapConfigProvider, definitions: ScanResult) -> ConfigProvider:
        models = definitions.get_components(component_type=ComponentTypeEnum.CONFIG_MODEL)
        self.configuration = ConfigProvider(bootstrap, models)
        logger.debug(
            "【ConfigStarter】已绑定配置模型：{}",
            ", ".join(model.__name__ for model in self.configuration.model_classes),
        )
        return self.configuration

    def close(self):
        self.configuration.close()
        logger.info("【ConfigStarter】应用配置快照已关闭")
