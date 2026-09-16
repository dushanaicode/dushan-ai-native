import logging
from threading import Lock


class SocketProtocolLogFilter(logging.Filter):
    """协议栈在 ASGI 之前记录原始握手/帧；共享日志接点按应用计数保护。

    不改变 logger 等级或 handler。框架记录安全连接/异常统计，SDK 警告保留安全摘要；
    非 WebSocket 的 Uvicorn 日志不受影响。
    """

    _names = (
        "uvicorn.error",
        "websockets.server",
        "websockets.protocol",
        "websockets.legacy.server",
    )
    _lock = Lock()
    _users = 0
    _instance = None

    def filter(self, record):
        path = record.pathname.replace("\\", "/")
        if record.name == "uvicorn.error" and "/websockets/" not in path:
            return True
        if record.levelno < logging.WARNING:
            return False
        return logging.LogRecord(
            record.name,
            record.levelno,
            record.pathname,
            record.lineno,
            "WebSocket 协议层异常，原始握手与帧已隔离",
            (),
            None,
            record.funcName,
        )

    @classmethod
    def acquire(cls):
        with cls._lock:
            if cls._users == 0:
                cls._instance = cls()
                for name in cls._names:
                    logging.getLogger(name).addFilter(cls._instance)
            cls._users += 1

    @classmethod
    def release(cls):
        with cls._lock:
            cls._users -= 1
            if cls._users == 0:
                for name in cls._names:
                    logging.getLogger(name).removeFilter(cls._instance)
                cls._instance = None
