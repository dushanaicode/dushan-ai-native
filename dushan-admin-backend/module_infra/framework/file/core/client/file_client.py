from __future__ import annotations

from typing import Protocol, runtime_checkable

from module_infra.framework.file.core.client.s3.s3_file_presigned_url_resp_dto import (
    FilePresignedUrlRespDTO,
)


@runtime_checkable
class FileClient(Protocol):
    """文件客户端接口"""

    def get_id(self) -> int:
        """获得客户端编号"""
        ...

    async def upload(self, path: str, content: bytes, file_type: str) -> str:
        """上传文件，返回 HTTP 访问地址"""
        ...

    async def delete(self, path: str) -> None:
        """删除文件"""
        ...

    async def get_content(self, path: str) -> bytes:
        """获得文件内容"""
        ...

    async def get_presigned_object_url(self, path: str) -> FilePresignedUrlRespDTO:
        """获得文件预签名地址（上传用）"""
        ...

    async def presign_get_url(self, path: str, expiration_seconds: int | None = None) -> str:
        """生成文件读取的预签名地址"""
        ...

    async def list_objects(self, prefix: str = "", delimiter: str = "/") -> dict:
        """
        列举指定前缀下的对象和公共前缀（子目录）

        :param prefix: 目录前缀，如 "images/2024/"（空字符串表示根目录）
        :param delimiter: 分隔符，默认 "/"
        :return: {
            "files": [{"key": "...", "name": "...", "size": 0, "lastModified": "..."}],
            "directories": [{"prefix": "...", "name": "..."}],
            "isTruncated": False,
            "nextMarker": ""
        }
        """
        ...

    async def rename(self, old_key: str, new_key: str) -> None:
        """重命名文件或目录"""
        ...

    async def close(self) -> None:
        """关闭客户端连接和资源"""
        ...
