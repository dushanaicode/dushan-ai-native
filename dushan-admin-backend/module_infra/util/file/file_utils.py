import hashlib
import os
import time

from module_infra.framework.file.core.utils.file_type_utils import FileTypeUtils


class FileUtils:
    """文件路径、名称、类型处理工具"""

    @staticmethod
    def generate_storage_path(
        original_name: str,
        directory: str | None = None,
        timestamp_suffix: bool = True,
    ) -> str:
        """生成文件存储路径"""
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
            extension = FileTypeUtils.get_extension(file_type)
            return f"{base_name}{extension}" if extension else base_name
        _, existing_extension = os.path.splitext(name)
        if not existing_extension and file_type:
            extension = FileTypeUtils.get_extension(file_type)
            if extension:
                return f"{name}{extension}"
        return name

    @staticmethod
    def rename_storage_key(old_key: str, new_name: str) -> str:
        """替换存储键名称，保留父路径和目录尾斜杠，由存储客户端校验最终键。"""
        parent, separator, _ = old_key.rstrip("/").rpartition("/")
        suffix = "/" if old_key.endswith("/") else ""
        return f"{parent}{separator}{new_name}{suffix}"
