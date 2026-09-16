from typing import Protocol


class SessionPolicy(Protocol):
    """上层记录策略只绑定受管 Session；不得拥有连接、事务或异步身份获取。"""

    def bind(self, session) -> None: ...

    def check(self, session) -> None: ...
