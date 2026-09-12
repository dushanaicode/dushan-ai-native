from dataclasses import dataclass, field


@dataclass(slots=True)
class DatabaseExecution:
    """一次请求或任务的路由与审计值，不持有 Session。"""

    account_id: str | None
    datasource: str | None
    include_deleted: bool
    active: bool = True
    written: bool = False
    generated_ids: list[int] = field(default_factory=list)
