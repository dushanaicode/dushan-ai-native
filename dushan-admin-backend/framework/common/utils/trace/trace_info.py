from typing import TypedDict


class TraceInfo(TypedDict):
    """表示当前或远端 W3C 链路标识，无有效链路时使用 None。"""

    trace_id: str | None
    span_id: str | None
    is_sampled: bool
