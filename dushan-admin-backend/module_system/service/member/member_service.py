from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MemberService(Protocol):
    async def get_member_user_mobile(self, id: int) -> str | None: ...

    async def get_member_user_email(self, id: int) -> str | None: ...
