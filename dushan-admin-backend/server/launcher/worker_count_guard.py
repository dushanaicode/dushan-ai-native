def resolve_effective_worker_count(workers: int, reload: bool) -> int:
    """确定实际进程数，开启热重载时固定为 1。"""
    if workers < 1:
        raise ValueError("服务器进程数必须大于零")
    return 1 if reload else workers
