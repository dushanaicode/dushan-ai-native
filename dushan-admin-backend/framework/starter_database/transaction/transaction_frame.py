import asyncio
from dataclasses import dataclass, field

from framework.starter_database.session.managed_async_session import ManagedAsyncSession
from framework.starter_database.transaction.commit_action import CommitAction


@dataclass(slots=True)
class TransactionFrame:
    session: ManagedAsyncSession
    source: str
    owner: asyncio.Task
    active: bool = True
    rollback_only: bool = False
    callbacks: list[CommitAction] = field(default_factory=list)
