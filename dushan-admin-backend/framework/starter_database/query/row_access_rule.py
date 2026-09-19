from abc import ABC, abstractmethod

from framework.common.exception.core.error_code import ErrorCode
from framework.starter_database.query.row_access_policy import RowAccessPolicy
from framework.starter_database.spi.session_policy import SessionPolicy


class RowAccessRule(SessionPolicy, ABC):
    """组件提供约束，Database 只安装一次 SQL/flush 处理和写入预检查。"""

    def bind(self, session):
        rules = tuple(rule for rule in session.access_policies if isinstance(rule, RowAccessRule))
        if rules[0] is self:
            session._row_access_policy = RowAccessPolicy(rules)
            session._row_access_policy.bind(session)

    def check(self, session):
        if session._row_access_policy.rules[0] is self:
            session._row_access_policy.check(session)

    @abstractmethod
    def scope_key(self): ...

    @abstractmethod
    def condition(self, config, operation, *, orm=False, entity=None): ...

    def prepare_insert(self, config, row):
        """默认不补字段；需要生成归属的规则显式覆盖。"""

    @abstractmethod
    def validate_row(self, config, row, operation): ...

    @abstractmethod
    def failure(self, reason: "ErrorCode"): ...
