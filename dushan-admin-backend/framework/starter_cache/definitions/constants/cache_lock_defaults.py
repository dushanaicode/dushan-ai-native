class CacheLockDefaults:
    """回源互斥锁的默认时序；临界区上界必须小于租约，调用方可逐次覆盖。"""

    LEASE_SECONDS = 30.0
    WAIT_SECONDS = 0.5
    CRITICAL_SECTION_TIMEOUT_SECONDS = 25.0
