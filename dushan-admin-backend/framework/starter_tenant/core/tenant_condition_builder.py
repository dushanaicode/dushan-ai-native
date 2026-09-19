from sqlalchemy import bindparam, true

from framework.starter_database.query.row_statement_filter import RowStatementFilter
from framework.starter_tenant.definitions.constants.tenant_error_codes import TenantErrorCodes
from framework.starter_tenant.exception.tenant_exception import TenantException


class TenantConditionBuilder(RowStatementFilter):
    def __init__(self, registry, context):
        super().__init__(registry, lambda: TenantException(TenantErrorCodes.MODEL))
        self.context = context

    def condition(self, config, operation, *, orm=False, entity=None):
        if config.public:
            return true()
        self.context.authorize_resource(config.table.key, operation)
        return self._column(config, config.tenant_column, orm, entity) == bindparam(
            "_dushan_tenant_scope", self.context.get_required_tenant_id(), unique=True
        )
