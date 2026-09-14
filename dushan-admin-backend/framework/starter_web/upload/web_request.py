from python_multipart.multipart import parse_options_header
from starlette.exceptions import HTTPException
from starlette.formparsers import MultiPartException
from starlette.requests import Request

from framework.starter_web.upload.multipart_parser import MultipartParser


class WebRequest(Request):
    """保持 Request 原生缓存与表单限制，仅为 multipart 选择可完整清理的原生子类。"""

    async def _get_form(self, *, max_files=1000, max_fields=1000, max_part_size=1024 * 1024):
        content_type, _ = parse_options_header(self.headers.get("content-type"))
        if self._form is None and content_type == b"multipart/form-data":
            parser = MultipartParser(
                self.headers,
                self.stream(),
                max_files=max_files,
                max_fields=max_fields,
                max_part_size=max_part_size,
            )
            try:
                self._form = await parser.parse()
            except MultiPartException as error:
                raise HTTPException(400, error.message) from error
            return self._form
        return await super()._get_form(
            max_files=max_files,
            max_fields=max_fields,
            max_part_size=max_part_size,
        )
