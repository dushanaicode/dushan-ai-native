from framework.starter_database.public import (
    DatabaseSettings,
)
from framework.starter_di.public import (
    Inject,
    framework,
    post_construct_hook,
)


@framework
class SystemRequirements:
    database: DatabaseSettings = Inject()

    @post_construct_hook
    def validate(self):
        if not self.database.enabled or self.database.id_strategy != "snowflake":
            raise ValueError(
                "system 模块要求启用 database、使用 snowflake 并为每个进程分配独立机器号"
            )
