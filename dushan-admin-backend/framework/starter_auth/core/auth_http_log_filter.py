import logging
from contextlib import contextmanager
from contextvars import ContextVar


class AuthHttpLogFilter(logging.Filter):
    """仅阻止本 HTTP 资源当前调用的 SDK 原始日志；其他调用及应用不受影响。"""

    _NAMES = ("httpx", "httpcore.connection", "httpcore.http11", "httpcore.http2", "httpcore.proxy")

    def __init__(self):
        super().__init__()
        self._quiet = ContextVar("auth_http_quiet", default=False)

    def filter(self, record):
        return not self._quiet.get()

    def open(self):
        for name in self._NAMES:
            logging.getLogger(name).addFilter(self)

    def close(self):
        for name in self._NAMES:
            logging.getLogger(name).removeFilter(self)

    @contextmanager
    def quiet(self):
        token = self._quiet.set(True)
        try:
            yield
        finally:
            self._quiet.reset(token)
