from fastapi import HTTPException


class RequestBodyLimit(HTTPException, OSError):
    """HTTP 413 分类，同时让原生 multipart parser 走文件清理分支。"""

    def __init__(self) -> None:
        HTTPException.__init__(self, 413, "请求体超过配置上限")
