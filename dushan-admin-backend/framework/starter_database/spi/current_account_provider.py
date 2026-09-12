from typing import Protocol


class CurrentAccountProvider(Protocol):
    """当前应用的审计账户适配，不建立进程全局 Security 服务引用。"""

    def get_current_account_id(self) -> str | None: ...
