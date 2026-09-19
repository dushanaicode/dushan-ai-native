from types import MappingProxyType

from framework.starter_database.definitions.constants.row_access_error_codes import (
    RowAccessErrorCodes,
)
from framework.starter_database.query.row_access_target import RowAccessTarget


class RowAccessRegistry:
    """同一 Session 的行规则共享表集合，避免一层遗漏另一层的读取来源。"""

    def __init__(self, rules):
        self.rules = rules
        keys = set(rules[0].registry.entries)
        if any(set(rule.registry.entries) != keys for rule in rules):
            raise rules[0].failure(RowAccessErrorCodes.CONFIGURATION)
        entries = {}
        for key in sorted(keys):
            configs = [rule.registry.entries[key] for rule in rules]
            first = configs[0]
            if any(
                config.table is not first.table or config.model is not first.model
                for config in configs
            ):
                raise rules[0].failure(RowAccessErrorCodes.CONFIGURATION)
            tenant_columns = {
                config.tenant_column for config in configs if config.tenant_column is not None
            }
            if len(tenant_columns) > 1:
                raise rules[0].failure(RowAccessErrorCodes.CONFIGURATION)
            entries[key] = RowAccessTarget(
                first.table,
                first.model,
                all(config.public and config.tenant_column is None for config in configs),
                next(iter(tenant_columns), None),
                tuple(sorted({name for config in configs for name in config.authority_columns})),
            )
        self.entries = MappingProxyType(entries)

    def require(self, table):
        for rule in self.rules:
            rule.registry.require(table)
        return self.entries[table.key]

    def require_mapper(self, mapper):
        for rule in self.rules:
            rule.registry.require_mapper(mapper)
        return self.entries[mapper.local_table.key]

    def validate_statement(self, statement):
        tables = set()
        for rule in self.rules:
            tables.update(rule.registry.validate_statement(statement))
        return tables
