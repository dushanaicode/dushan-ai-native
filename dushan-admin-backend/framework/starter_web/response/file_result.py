import asyncio
import io
from collections.abc import AsyncGenerator, Mapping
from pathlib import Path
from urllib.parse import quote

from fastapi.responses import FileResponse, Response

from framework.starter_web.config.response_settings import ResponseSettings
from framework.starter_web.response.media_type_constants import MediaTypeConstants
from framework.starter_web.response.response_headers import ResponseHeaders
from framework.starter_web.response.streaming_result import StreamingResult


class FileResult:
    """使用标准响应发送已授权的磁盘文件或预生成内存数据。

    download 由 FileResponse 处理磁盘分块、HEAD和Range；from_bytes/excel有内存大小上限。
    调用方先确认文件访问权限与主动内容安全，传入路径本身不代表已经获得授权。
    """

    def __init__(self, settings: ResponseSettings) -> None:
        """保存当前应用的下载策略，不使用全局可变配置。"""
        self.settings = settings

    def download(
        self,
        file_path: str | Path,
        file_name: str | None = None,
        media_type: str | None = None,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> FileResponse:
        """检查文件后交给标准文件响应，显示文件名不改变实际读取路径。"""
        path = Path(file_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"文件不存在: {path}")
        name = path.name if file_name is None else file_name
        response = FileResponse(
            path=path, filename=name, media_type=media_type, headers=self._headers(name, headers)
        )
        response.chunk_size = self.settings.file_chunk_size
        return response

    def from_bytes(
        self,
        file_data: bytes | io.BytesIO,
        file_name: str,
        media_type: str = MediaTypeConstants.OCTET_STREAM,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> Response:
        """发送有界内存内容，不修改或关闭调用方的 BytesIO。"""
        self._check_memory_limit(file_data)
        payload = file_data.getvalue() if isinstance(file_data, io.BytesIO) else file_data
        return Response(
            content=payload, media_type=media_type, headers=self._headers(file_name, headers)
        )

    def excel(self, excel_data: bytes | io.BytesIO, file_name: str) -> Response:
        """发送已生成的 XLSX 内容，不承担工作簿生成或数据库导出。"""
        return self.from_bytes(excel_data, file_name, media_type=MediaTypeConstants.XLSX)

    def stream_bytes(
        self,
        file_data: bytes | io.BytesIO,
        file_name: str,
        media_type: str = MediaTypeConstants.OCTET_STREAM,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> StreamingResult:
        """按配置块大小发送已生成内存内容，传输期间调用方不能改写或关闭缓冲区。

        该方法限制传输时的额外拷贝，不负责降低文件生成阶段的内存占用；
        大文件优先使用download(path)，或由业务提供真正按需生成的异步生成器。
        """
        size = self._check_memory_limit(file_data)
        response_headers = self._headers(file_name, headers)
        if "content-length" in response_headers and response_headers["content-length"] != str(size):
            raise ValueError("声明的 Content-Length 与内存内容长度不一致")
        response_headers["content-length"] = str(size)
        return StreamingResult(
            self._memory_chunks(file_data),
            media_type=media_type,
            headers=response_headers,
        )

    def excel_stream(self, excel_data: bytes | io.BytesIO, file_name: str) -> StreamingResult:
        """分块发送已生成的XLSX内容，复用流关闭与内存边界。"""
        return self.stream_bytes(excel_data, file_name, media_type=MediaTypeConstants.XLSX)

    def _check_memory_limit(self, file_data: bytes | io.BytesIO) -> int:
        """读取已生成内容的长度并检查上限，不修改缓冲区游标。"""
        if isinstance(file_data, io.BytesIO):
            with file_data.getbuffer() as view:
                size = view.nbytes
        else:
            size = len(file_data)
        if size > self.settings.max_memory_bytes:
            raise ValueError("内存下载超过配置上限，请使用磁盘文件或生成器")
        return size

    async def _memory_chunks(self, file_data: bytes | io.BytesIO) -> AsyncGenerator[bytes, None]:
        """在开始迭代时借用缓冲区视图，关闭生成器时归还，始终保持调用方游标。"""
        with (
            file_data.getbuffer()
            if isinstance(file_data, io.BytesIO)
            else memoryview(file_data) as view
        ):
            for offset in range(0, view.nbytes, self.settings.file_chunk_size):
                yield view[offset : offset + self.settings.file_chunk_size].tobytes()
                await asyncio.sleep(0)

    def _headers(self, file_name: str, headers: Mapping[str, str] | None) -> dict[str, str]:
        """设置安全默认缓存和文件名，其他业务头继续保留。"""
        if (
            not file_name
            or file_name in (".", "..")
            or any(char in "/\\" or ord(char) < 32 or ord(char) == 127 for char in file_name)
        ):
            raise ValueError("下载显示文件名不能包含路径或控制字符")
        result = ResponseHeaders.with_language(headers)
        disposition = "attachment" if self.settings.attachment else "inline"
        result["content-disposition"] = (
            f"{disposition}; filename*=UTF-8''{quote(file_name, safe='')}"
        )
        exposed = [
            item.strip()
            for item in result.get("access-control-expose-headers", "").split(",")
            if item.strip()
        ]
        if not any(item.lower() == "content-disposition" for item in exposed):
            exposed.append("Content-Disposition")
        result["access-control-expose-headers"] = ", ".join(exposed)
        result["cache-control"] = (
            "no-store"
            if self.settings.download_cache == "no-store"
            else f"{self.settings.download_cache}, max-age={self.settings.download_max_age}"
        )
        return result
