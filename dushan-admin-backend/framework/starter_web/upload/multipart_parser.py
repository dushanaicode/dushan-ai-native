from starlette.formparsers import MultiPartException, MultiPartParser

from framework.common.utils.cleanup_utils import CleanupUtils


class MultipartParser(MultiPartParser):
    """复用原生解析，只补中途取消、断连及截断 multipart 的临时文件清理。"""

    async def parse(self):
        self._complete = False
        try:
            result = await super().parse()
            if not self._complete:
                raise MultiPartException("Multipart body is incomplete")
            return result
        except BaseException as primary:
            # Starlette 1.3.1 只在 MultiPartException/OSError 时关闭这些已创建文件。
            errors = []
            for file in self._files_to_close_on_error:
                try:
                    file.close()
                except BaseException as error:
                    errors.append(error)
            CleanupUtils.raise_collected_cleanup_errors(
                "multipart 解析及文件关闭失败", errors, primary_error=primary
            )

    def on_end(self) -> None:
        self._complete = True
        super().on_end()
