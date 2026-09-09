"""进程数量的基础约束。"""


def resolve_effective_worker_count(workers: int, reload: bool) -> int:
    """热重载固定使用单进程，正常模式采用已校验的进程数。"""
    if workers < 1:
        raise ValueError("服务器进程数必须大于零")
    return 1 if reload else workers
