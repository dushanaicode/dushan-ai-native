from framework.common.enums.base_enum import BaseEnum


class ComponentRoleEnum(BaseEnum):
    """DI 组件角色；只供容器分类，scanner 不解释这些业务语义。"""

    SERVICE = ("service", "服务")
    REPOSITORY = ("repository", "仓储")
    MAPPER = ("mapper", "映射器")
    AGGREGATE_MAPPER = ("aggregate_mapper", "聚合映射器")
    DAO = ("dao", "数据访问")
    FRAMEWORK = ("framework", "框架组件")
    STARTER = ("starter", "启动组件")
    UTIL = ("util", "工具组件")
    WEBSOCKET = ("websocket", "WebSocket 组件")
    REDIS = ("redis", "Redis 组件")
    CONFIG_BUILDER = ("config_builder", "配置构造器")
    BOOTSTRAP = ("bootstrap", "引导组件")
