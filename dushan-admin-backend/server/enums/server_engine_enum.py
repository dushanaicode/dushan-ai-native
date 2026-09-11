from framework.common.enums.base_enum import BaseEnum


class ServerEngineEnum(BaseEnum):
    """声明可选 HTTP 引擎，默认选择由 application.yaml 提供。"""

    GRANIAN = ("granian", "Granian")
    UVICORN = ("uvicorn", "Uvicorn")
