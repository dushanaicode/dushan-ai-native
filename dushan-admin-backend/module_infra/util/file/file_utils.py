"""文件模块工具类"""

import hashlib
import mimetypes
import os


class FileUtils:
    """文件路径、名称、类型处理工具"""

    @staticmethod
    def generate_storage_path(
        original_name: str,
        directory: str | None = None,
        timestamp_suffix: bool = True,
    ) -> str:
        """生成文件存储路径"""
        import time

        current_name = original_name
        if timestamp_suffix:
            main_name, ext_name = os.path.splitext(current_name)
            current_name = f"{main_name}_{int(time.time() * 1000)}{ext_name}"

        path_parts = []
        if directory:
            path_parts.append(directory.rstrip("/"))
        path_parts.append(current_name)
        return "/".join(path_parts)

    @staticmethod
    def resolve_file_name(name: str | None, content: bytes, file_type: str | None) -> str:
        """
        根据原始文件名、内容和MIME类型，生成最终的逻辑文件名。
        - 无名称时用 SHA256 哈希作为文件名
        - 无扩展名时根据 MIME 类型补充
        """
        if not name:
            base_name = hashlib.sha256(content).hexdigest()
            extension = FileUtils.get_extension_from_mime(file_type)
            return f"{base_name}{extension}" if extension else base_name
        if not os.path.splitext(name)[1] and file_type:
            extension = FileUtils.get_extension_from_mime(file_type)
            if extension:
                return f"{name}{extension}"
        return name

    @staticmethod
    def get_extension_from_mime(mime_type: str | None) -> str | None:
        """根据 MIME 类型获得文件后缀"""
        if not mime_type:
            return None
        extension = mimetypes.guess_extension(mime_type.lower(), strict=False)
        if extension == ".jpe":
            return ".jpg"
        if extension == ".htm":
            return ".html"
        return extension

    @staticmethod
    def get_mime_type_from_name(name: str) -> str | None:
        """根据文件名猜测 MIME 类型"""
        if not name:
            return None
        mime_type, _ = mimetypes.guess_type(name, strict=True)
        return mime_type
