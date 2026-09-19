from __future__ import annotations

from framework.common.schemas import BaseVO


class FilePresignedUrlRespDTO(BaseVO):
    """文件预签名地址 Response DTO"""

    upload_url: str
    url: str
