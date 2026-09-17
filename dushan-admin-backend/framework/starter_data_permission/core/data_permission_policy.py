from framework.starter_data_permission.core.condition_builder import ConditionBuilder
from framework.starter_data_permission.exception.data_permission_exception import (
    DataPermissionException,
)
from framework.starter_database.query.row_access_rule import RowAccessRule


class DataPermissionPolicy(RowAccessRule):
    """数据范围规则；与租户隔离共用一次 SQL 改写和完整写入预检查。"""

    def __init__(self, registry, service):
        self.registry, self.service = registry, service
        self.builder = ConditionBuilder(registry, service)

    def scope_key(self):
        return self.service.execution_key()

    def condition(self, config, operation, *, orm=False, entity=None):
        return self.builder.condition(config, operation, orm=orm, entity=entity)

    def failure(self, reason):
        return DataPermissionException(reason)

    def validate_row(self, config, row, operation):
        if config.public and config.tenant_column is None:
            return
        if config.public:
            identity = self.service.security.current() or self.service.security.current_workload()
            if (
                identity is None
                or identity.tenant_id is None
                or row.get(config.tenant_column) != identity.tenant_id
            ):
                raise DataPermissionException("write")
            return
        frame = self.service.current()
        for name in config.authority_columns:
            if name not in row or (
                row[name] is not None
                and type(row[name]) is not config.table.c[name].type.python_type
            ):
                raise DataPermissionException("write")
        if (
            frame.identity.tenant_id is None
            or row[config.tenant_column] != frame.identity.tenant_id
        ):
            raise DataPermissionException("write")
        if (
            config.public
            or self.service.is_exempt(config.resource, operation)
            or frame.grant.tenant_all
        ):
            return
        if not (
            config.membership_column is not None
            and row[config.membership_column]
            in config.scope_values(config.membership_column, frame.grant.membership_ids)
            or config.department_column is not None
            and row[config.department_column]
            in config.scope_values(config.department_column, frame.grant.department_ids)
        ):
            raise DataPermissionException("write")
