from sqlalchemy import false

from framework.starter_database.query.row_statement_filter import RowStatementFilter
from framework.starter_database.query.soft_delete_registry import SoftDeleteRegistry


class SoftDeleteFilter(RowStatementFilter):
    """复用行过滤的别名、关联和子查询处理，保持外连接的空侧。"""

    def __init__(self, statement):
        # 单纯软删除条件不引入行权限对 ORM 递归 CTE 的额外限制。
        super().__init__(SoftDeleteRegistry(statement), None)

    def condition(self, config, operation, *, orm=False, entity=None):
        return self._column(config, "deleted", orm, entity) == false()
