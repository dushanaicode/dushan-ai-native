from framework.starter_database.query.row_access_rule import RowAccessRule
from framework.starter_tenant.core.tenant_condition_builder import TenantConditionBuilder
from framework.starter_tenant.exception.tenant_exception import TenantException


class TenantSessionPolicy(RowAccessRule):
    """租户归属和资源授权规则；数据库统一完成语句重写、锁定和写入检查。"""

    def __init__(self, registry, context):
        self.registry, self.context = registry, context
        self.builder = TenantConditionBuilder(registry, context)

    def scope_key(self):
        return self.context.current()

    def condition(self, config, operation, *, orm=False, entity=None):
        return self.builder.condition(config, operation, orm=orm, entity=entity)

    def prepare_insert(self, config, row):
        if not config.public and config.tenant_column not in row:
            row[config.tenant_column] = self.context.get_required_tenant_id()

    def validate_row(self, config, row, operation):
        if config.public:
            return
        self.context.authorize_resource(config.table.key, operation)
        if row[config.tenant_column] != self.context.get_required_tenant_id():
            raise TenantException("write")

    def failure(self, reason):
        return TenantException({"configuration": "model", "stale": "expired"}.get(reason, reason))
