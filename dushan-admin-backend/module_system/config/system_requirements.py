from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_di.decorators.components import framework
from framework.starter_di.decorators.inject import Inject
from framework.starter_di.decorators.lifecycle import post_construct_hook


@framework
class SystemRequirements:
    database: DatabaseSettings = Inject()

    @post_construct_hook
    def validate(self):
        if not self.database.enabled or self.database.id_strategy != "snowflake":
            raise ValueError(
                "system 模块要求启用 database、使用 snowflake 并为每个进程分配独立机器号"
            )
