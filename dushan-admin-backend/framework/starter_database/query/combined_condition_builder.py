from sqlalchemy import and_

from framework.starter_database.query.row_statement_filter import RowStatementFilter


class CombinedConditionBuilder(RowStatementFilter):
    """先组合全部读条件再重写，写入预检查不会读取另一策略隐藏的数据。"""

    def __init__(self, registry, rules):
        super().__init__(registry, lambda: rules[0].failure("configuration"))
        self.rules = rules

    def condition(self, config, operation, *, orm=False, entity=None):
        return and_(
            *(
                rule.condition(
                    rule.registry.require(config.table), operation, orm=orm, entity=entity
                )
                for rule in self.rules
            )
        )
