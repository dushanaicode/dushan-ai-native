from typing import Final


class MediaTypeConstants:
    """常用媒体类型常量。"""

    # 通用二进制流，适合未知类型文件下载。
    OCTET_STREAM: Final[str] = "application/octet-stream"
    # Excel xlsx 文件。
    XLSX: Final[str] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    # JSON 响应。
    JSON: Final[str] = "application/json"
    # Server-Sent Events 事件流。
    EVENT_STREAM: Final[str] = "text/event-stream"
