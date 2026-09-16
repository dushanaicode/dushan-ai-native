from sqlalchemy import and_, bindparam, false, or_, true

from framework.starter_data_permission.exception.data_permission_exception import (
    DataPermissionException,
)
from framework.starter_database.query.row_statement_filter import RowStatementFilter


class ConditionBuilder(RowStatementFilter):
    """在统一行过滤机制上计算租户内的成员、部门及豁免条件。"""

    def __init__(self, registry, service):
        super().__init__(registry, lambda: DataPermissionException("configuration"))
        self.service = service

    def condition(self, config, operation, *, orm=False, entity=None):
        if config.public and config.tenant_column is None:
            return true()
        frame = self.service.current()
        if frame.identity.tenant_id is None:
            return false()
        tenant = self._column(config, config.tenant_column, orm, entity) == bindparam(
            "_dushan_dp_tenant", frame.identity.tenant_id, unique=True
        )
        if config.public or self.service.is_exempt(config.resource, operation):
            return tenant
        grant = frame.grant
        if grant.tenant_all:
            return tenant
        conditions = []
        for name, values in (
            (config.membership_column, grant.membership_ids),
            (config.department_column, grant.department_ids),
        ):
            if name is not None and values:
                size = self.service.settings.in_clause_chunk_size
                ordered = sorted(values)
                conditions.extend(
                    self._column(config, name, orm, entity).in_(
                        bindparam(
                            "_dushan_dp_scope",
                            ordered[start : start + size],
                            expanding=True,
                            unique=True,
                        )
                    )
                    for start in range(0, len(ordered), size)
                )
        return and_(tenant, or_(*conditions) if conditions else false())
