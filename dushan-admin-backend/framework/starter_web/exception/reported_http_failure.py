class ReportedHttpFailure(RuntimeError):
    """原始故障已在请求归属内安全记录；宿主只收到不含原始载荷的中止信号。"""

    def __init__(self, owner: str) -> None:
        self.owner = owner
        super().__init__(f"DUSHAN_RECORDED_HTTP_FAILURE {owner}")
