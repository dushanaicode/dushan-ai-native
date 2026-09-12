from typing import Protocol

from framework.starter_database.connection.query_observation import QueryObservation


class QueryObserver(Protocol):
    """仅接受脱敏事件的同步消费者；不得返回协程或执行数据库 I/O。"""

    def observe(self, observation: QueryObservation) -> None: ...
