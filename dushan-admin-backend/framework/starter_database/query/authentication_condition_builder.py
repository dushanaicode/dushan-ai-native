from sqlalchemy import and_, false, true

from framework.starter_database.query.row_statement_filter import RowStatementFilter


class AuthenticationConditionBuilder(RowStatementFilter):
    """认证读取始终限定服务端租户，并隐藏软删除记录。"""

    def __init__(self, registry, tenant_id):
        super().__init__(registry, lambda: ValueError("认证读取声明无效"))
        self.tenant_id = tenant_id

    def condition(self, config, operation, *, orm=False, entity=None):
        conditions = []
        if config.tenant_column is not None:
            conditions.append(
                self._column(config, config.tenant_column, orm, entity) == self.tenant_id
            )
        if "deleted" in config.table.c:
            conditions.append(self._column(config, "deleted", orm, entity) == false())
        return and_(*conditions) if conditions else true()
