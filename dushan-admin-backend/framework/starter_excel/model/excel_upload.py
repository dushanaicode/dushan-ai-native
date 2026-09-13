from typing import BinaryIO, Protocol


class ExcelUpload(Protocol):
    """兼容原生 UploadFile 的文件契约；上传流归调用方所有且必须可定位。"""

    filename: str | None
    content_type: str | None
    file: BinaryIO
