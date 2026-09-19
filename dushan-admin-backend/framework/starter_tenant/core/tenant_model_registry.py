from types import MappingProxyType

from loguru import logger
from sqlalchemy import Column, Delete, Insert, Table, UniqueConstraint, Update
from sqlalchemy.orm import Mapper
from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import ColumnClause
from sqlalchemy.sql.selectable import Select, TableClause

from framework.starter_tenant.definitions.constants.tenant_error_codes import TenantErrorCodes
from framework.starter_tenant.definitions.enums.tenant_model_kind import TenantModelKind
from framework.starter_tenant.entity.tenant_base_do import TenantBaseDO
from framework.starter_tenant.exception.tenant_exception import TenantException
from framework.starter_tenant.model.tenant_model import TenantModel


class TenantModelRegistry:
    """应用模型的唯一所有权快照；未知表与伪造的同名 Table 均拒绝。"""

    def __init__(self, models):
        logger.info("【TenantStarter 】开始登记租户模型与校验隔离约束")
        entries = {}
        for model in models:
            item = model if isinstance(model, TenantModel) else vars(model).get("__tenant_model__")
            if item is None and isinstance(model, type) and issubclass(model, TenantBaseDO):
                item = TenantModel(model, TenantModelKind.TENANT, "tenant_id")
            if not isinstance(item, TenantModel) or item.table.key in entries:
                raise TenantException(TenantErrorCodes.MODEL)
            entries[item.table.key] = item

        self.entries = MappingProxyType(entries)
        for item in entries.values():
            unique = [
                constraint.columns
                for constraint in item.table.constraints
                if isinstance(constraint, UniqueConstraint)
            ]
            unique.extend(index.columns for index in item.table.indexes if index.unique)
            if not item.public and any(item.tenant_column not in columns for columns in unique):
                raise TenantException(TenantErrorCodes.MODEL)
            for foreign_key in item.table.foreign_key_constraints:
                other = self.require(foreign_key.referred_table)
                if other.public:
                    continue
                pairs = {
                    (element.parent.key, element.column.key) for element in foreign_key.elements
                }
                if item.public or (item.tenant_column, other.tenant_column) not in pairs:
                    raise TenantException(TenantErrorCodes.MODEL)
        logger.info(
            "【TenantStarter 】模型校验完成：租户表 {} 个，全局表 {} 个",
            sum(not item.public for item in entries.values()),
            sum(item.public for item in entries.values()),
        )

    def require(self, table):
        item = self.entries.get(table.key)
        if item is None or table._deannotate() is not item.table:
            raise TenantException(TenantErrorCodes.MODEL)
        return item

    def require_mapper(self, mapper: Mapper):
        item = self.require(mapper.local_table)
        if item.model is not mapper.class_:
            raise TenantException(TenantErrorCodes.MODEL)
        return item

    def validate_statement(self, statement):
        tables, seen, pending = set(), set(), [statement]
        while pending:
            node = pending.pop()
            if id(node) in seen:
                continue
            seen.add(id(node))
            if isinstance(node, (Insert, Update, Delete)) and node is not statement:
                raise TenantException(TenantErrorCodes.MODEL)
            if isinstance(node, Select) and (
                node._prefixes or node._suffixes or node._hints or node._statement_hints
            ):
                raise TenantException(TenantErrorCodes.MODEL)
            if isinstance(node, (Insert, Update, Delete)) and (node._prefixes or node._hints):
                raise TenantException(TenantErrorCodes.MODEL)
            entity = node._annotations.get("parententity")
            if entity is not None:
                self.require_mapper(entity.mapper if entity.is_aliased_class else entity)
            if isinstance(node, TableClause) and not isinstance(node, Table):
                raise TenantException(TenantErrorCodes.MODEL)
            if (
                isinstance(node, ColumnClause)
                and node.is_literal
                and str(node.name) not in {"1", "*"}
            ):
                raise TenantException(TenantErrorCodes.MODEL)
            if isinstance(node, Table):
                self.require(node)
                tables.add(node._deannotate())
            if isinstance(node, Column) and isinstance(node.table, Table):
                self.require(node.table)
                tables.add(node.table._deannotate())
            if isinstance(node, Select):
                pending.extend(node.selected_columns)
                for source in node.get_final_froms():
                    pending.extend(visitors.iterate(source))
            pending.extend(node.get_children())
        return tables
