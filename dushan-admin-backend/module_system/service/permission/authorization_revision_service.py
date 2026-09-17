from typing import Protocol, runtime_checkable


@runtime_checkable
class AuthorizationRevisionService(Protocol):
    async def advance(self) -> None: ...
