from framework.common.schemas import BaseBO


class FileContentBO(BaseBO):
    name: str
    type: str
    content: bytes
