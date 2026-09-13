from framework.starter_cache.exception.cache_lock_exception import CacheLockException


class CacheLockContentionException(CacheLockException):
    """等待上界内锁仍被其他持有者占用；这是正常竞争结果，调用方可以退避后重试。"""
