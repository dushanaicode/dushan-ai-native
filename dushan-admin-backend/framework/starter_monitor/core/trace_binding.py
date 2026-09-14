from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, ClassVar


@dataclass(slots=True)
class TraceBinding:
    """绑定当前应用和Span的作用域；退出后撤销继承副本的继续使用许可。"""

    owner: Any
    span: Any
    active: bool = True
    current: ClassVar[ContextVar["TraceBinding | None"]] = ContextVar(
        "monitor_binding", default=None
    )
