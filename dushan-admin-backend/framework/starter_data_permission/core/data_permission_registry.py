from types import MappingProxyType

from loguru import logger
from sqlalchemy import Column, Delete, Insert, Table, Update
from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import ColumnClause, TextClause
from sqlalchemy.sql.selectable import Select, TableClause

from framework.starter_data_permission.definitions.constants.data_permission_error_codes import (
    DataPermissionErrorCodes,
)
from framework.starter_data_permission.exception.data_permission_exception import (
    DataPermissionException,
)
from framework.starter_data_permission.model.data_permission_model import DataPermissionModel
from framework.starter_tenant.entity.global_control_do import GlobalControlDO
from framework.starter_tenant.entity.tenant_base_do import TenantBaseDO


class DataPermissionRegistry:
    """只持有当前应用扫描的模型；不查询进程全局 Mapper 注册表。"""

    def __init__(self, models):
        logger.info("【DataPermissionStarter】开始登记数据权限模型")
        entries = {}
        for model in models:
            config = (
                model
                if isinstance(model, DataPermissionModel)
                else vars(model).get("__data_permission__")
            )
            if config is None and isinstance(model, type):
                if issubclass(model, TenantBaseDO):
                    config = DataPermissionModel(model, True, "tenant_id")
                elif issubclass(model, GlobalControlDO):
                    config = DataPermissionModel(model, True, None)
            if not isinstance(config, DataPermissionModel):
                raise DataPermissionException(DataPermissionErrorCodes.UNREGISTERED)
            if config.table.key in entries:
                raise DataPermissionException(DataPermissionErrorCodes.CONFIGURATION)
            entries[config.table.key] = config
        self.entries = MappingProxyType(entries)
        logger.info(
            "【DataPermissionStarter】模型登记完成：记录范围受控 {} 个，公开范围 {} 个",
            sum(not item.public for item in entries.values()),
            sum(item.public for item in entries.values()),
        )

    def require(self, table):
        config = self.entries.get(table.key)
        if config is None:
            raise DataPermissionException(DataPermissionErrorCodes.UNREGISTERED)
        if table._deannotate() is not config.table:
            raise DataPermissionException(DataPermissionErrorCodes.CONFIGURATION)
        return config

    def require_mapper(self, mapper):
        config = self.require(mapper.local_table)
        if config.model is not mapper.class_:
            raise DataPermissionException(DataPermissionErrorCodes.UNREGISTERED)
        return config

    def _validate_entity(self, node):
        entity = node._annotations.get("parententity")
        if entity is not None:
            self.require_mapper(entity.mapper if entity.is_aliased_class else entity)

    def validate_statement(self, statement):
        tables = set()
        pending = [statement]
        seen = set()
        while pending:
            node = pending.pop()
            if id(node) in seen:
                continue
            seen.add(id(node))
            pending.extend(node.get_children())
            self._validate_entity(node)
            # ORM 属性表达式由 before_flush 直接送检，不经过 ManagedSession.execute。
            if isinstance(node, TextClause):
                raise DataPermissionException(DataPermissionErrorCodes.CONFIGURATION)
            if isinstance(node, (Insert, Update, Delete)) and node is not statement:
                raise DataPermissionException(DataPermissionErrorCodes.CONFIGURATION)
            if isinstance(node, Select) and (
                node._prefixes or node._suffixes or node._hints or node._statement_hints
            ):
                raise DataPermissionException(DataPermissionErrorCodes.CONFIGURATION)
            if isinstance(node, (Insert, Update, Delete)) and (node._prefixes or node._hints):
                raise DataPermissionException(DataPermissionErrorCodes.CONFIGURATION)
            if isinstance(node, TableClause) and not isinstance(node, Table):
                raise DataPermissionException(DataPermissionErrorCodes.UNREGISTERED)
            if (
                isinstance(node, ColumnClause)
                and node.is_literal
                and str(node.name) not in {"1", "*"}
            ):
                raise DataPermissionException(DataPermissionErrorCodes.CONFIGURATION)
            if isinstance(node, Table):
                self.require(node)
                tables.add(node._deannotate())
            if isinstance(node, Column) and isinstance(node.table, Table):
                self.require(node.table)
                tables.add(node.table._deannotate())
            if isinstance(node, Select):
                # select(Model) 的 column_property 在普通 Table 遍历中不可见。
                pending.extend(node.selected_columns)
                # joinedload 的隐式目标在 ORM 编译后的 FROM 中，必须一并核验。
                for source in node.get_final_froms():
                    pending.extend(visitors.iterate(source))
        return tables
