from __future__ import annotations

import mimetypes

import filetype


class FileTypeUtils:
    """文件类型检测和MIME类型处理工具"""

    _CUSTOM_MIME_TO_EXTENSION_MAP = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "application/pdf": ".pdf",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.ms-excel": ".xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.ms-powerpoint": ".ppt",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    }

    @staticmethod
    def get_mime_type_from_name(name: str) -> str | None:
        """已知文件名，获取文件类型"""
        if not name:
            return None
        mime_type, _ = mimetypes.guess_type(name, strict=True)
        return mime_type

    @staticmethod
    def get_mime_type(data: bytes | None, name: str | None = None) -> str:
        """获取文件的MIME类型"""
        mime_type: str | None = None
        if data and len(data) > 0:
            kind = filetype.guess(data)
            if kind is not None:
                mime_type = kind.mime
        if name and (not mime_type or mime_type == "application/octet-stream"):
            guessed_type_from_name = FileTypeUtils.get_mime_type_from_name(name)
            if guessed_type_from_name and guessed_type_from_name != "application/octet-stream":
                mime_type = guessed_type_from_name
            elif not mime_type:
                mime_type = guessed_type_from_name
        return mime_type or "application/octet-stream"

    @staticmethod
    def get_extension(mime_type: str | None) -> str | None:
        """根据 MIME 类型获得文件后缀"""
        if not mime_type:
            return None
        mime_type_lower = mime_type.lower()
        if mime_type_lower in FileTypeUtils._CUSTOM_MIME_TO_EXTENSION_MAP:
            return FileTypeUtils._CUSTOM_MIME_TO_EXTENSION_MAP[mime_type_lower]
        extension = mimetypes.guess_extension(mime_type_lower, strict=False)
        if extension == ".jpe":
            return ".jpg"
        if extension == ".htm":
            return ".html"
        return extension
