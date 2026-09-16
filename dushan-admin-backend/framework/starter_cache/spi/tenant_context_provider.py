from typing import Protocol


class TenantContextProvider(Protocol):
    """租户归属由受控执行提供；无上下文必须抛错，不能返回默认或全局范围。"""

    def get_required_tenant_id(self) -> str: ...
